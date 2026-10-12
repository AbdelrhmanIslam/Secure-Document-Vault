import io
import os
import uuid

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from decorators import login_required, role_required
from documents.crypto_utils import compute_hash, decrypt_file, encrypt_file, sign_data
from documents.services import (
    delete_document_record,
    delete_user_and_documents,
    user_can_delete_document,
    user_can_download_document,
    user_can_review_document,
    verify_document_record,
)
from extensions import db
from models import Document, User

docs_bp = Blueprint('documents', __name__)


def _ordered_documents_query():
    return Document.query.options(joinedload(Document.uploader), joinedload(Document.reviewed_by)).order_by(Document.upload_date.desc())


def _active_admin_count():
    return User.query.filter_by(role=User.ROLE_ADMIN, is_active=True).count()


def _get_allowed_extensions():
    return ', '.join(f'.{ext}' for ext in sorted(current_app.config['ALLOWED_EXTENSIONS']))


@docs_bp.route('/dashboard')
@login_required
def dashboard():
    user = g.current_user
    if user.role == User.ROLE_ADMIN:
        documents = _ordered_documents_query().all()
    else:
        documents = _ordered_documents_query().filter_by(uploader_id=user.id).all()

    return render_template(
        'dashboard.html',
        user=user,
        documents=documents,
        can_review_documents=user.can_review_documents(),
        can_manage_users=user.can_manage_users(),
    )


@docs_bp.route('/review')
@login_required
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER)
def manager_dashboard():
    documents = _ordered_documents_query().all()
    document_statuses = {document.id: verify_document_record(document) for document in documents}
    verified_count = sum(1 for status in document_statuses.values() if status['integrity_ok'])
    return render_template(
        'manager_dashboard.html',
        documents=documents,
        document_statuses=document_statuses,
        verified_count=verified_count,
    )


@docs_bp.route('/status/<int:doc_id>', methods=['POST'])
@login_required
@role_required(User.ROLE_ADMIN, User.ROLE_MANAGER)
def update_status(doc_id):
    document = Document.query.get_or_404(doc_id)
    new_status = request.form.get('status')
    
    if new_status in [Document.STATUS_PENDING, Document.STATUS_APPROVED, Document.STATUS_REJECTED]:
        if new_status == Document.STATUS_APPROVED:
            verification = verify_document_record(document)
            if not verification['integrity_ok']:
                flash('Cannot approve document: integrity verification failed.', 'error')
                return redirect(url_for('documents.manager_dashboard'))
                
        document.status = new_status
        document.reviewed_by_id = g.current_user.id
        db.session.commit()
        flash(f'Document status updated to {new_status}.', 'success')
    else:
        flash('Invalid status.', 'error')
        
    return redirect(url_for('documents.manager_dashboard'))

@docs_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file_storage = request.files.get('file')
        if not file_storage or not file_storage.filename:
            return render_template('upload.html', error='No file selected.', allowed_extensions=_get_allowed_extensions())

        original_filename = file_storage.filename
        safe_filename = secure_filename(original_filename)
        if not safe_filename:
            return render_template('upload.html', error='The selected filename is invalid.', allowed_extensions=_get_allowed_extensions())
        if '.' not in safe_filename:
            return render_template('upload.html', error='Files must include a valid extension.', allowed_extensions=_get_allowed_extensions())

        extension = safe_filename.rsplit('.', 1)[-1].lower()
        if extension not in current_app.config['ALLOWED_EXTENSIONS']:
            return render_template(
                'upload.html',
                error=f'File type not allowed. Allowed types: {_get_allowed_extensions()}.',
                allowed_extensions=_get_allowed_extensions(),
            )

        file_data = file_storage.read()
        file_size = len(file_data)
        if file_size == 0:
            return render_template('upload.html', error='Empty files cannot be uploaded.', allowed_extensions=_get_allowed_extensions())
        if file_size > current_app.config['MAX_CONTENT_LENGTH']:
            return render_template('upload.html', error='File too large.', allowed_extensions=_get_allowed_extensions())

        encrypted_data = encrypt_file(file_data)
        file_hash = compute_hash(file_data)
        signature = sign_data(file_hash.encode(), current_app.config['PRIVATE_KEY'])
        unique_name = f'{uuid.uuid4()}.enc'
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        encrypted_path = os.path.join(upload_dir, unique_name)

        with open(encrypted_path, 'wb') as file_handle:
            file_handle.write(encrypted_data)

        document = Document(
            filename=unique_name,
            original_filename=safe_filename,
            file_size=file_size,
            uploader_id=g.current_user.id,
            encrypted_path=encrypted_path,
            file_hash=file_hash,
            signature=signature,
        )
        db.session.add(document)
        db.session.commit()
        flash('Document uploaded, encrypted, and signed successfully.', 'success')
        return redirect(url_for('documents.dashboard'))

    return render_template('upload.html', allowed_extensions=_get_allowed_extensions())


@docs_bp.route('/metadata/<int:doc_id>')
@login_required
def metadata(doc_id):
    document = _ordered_documents_query().filter_by(id=doc_id).first_or_404()
    if not user_can_review_document(g.current_user, document):
        abort(403)

    verification = verify_document_record(document)
    return render_template('document_metadata.html', document=document, verification=verification)


@docs_bp.route('/download/<int:doc_id>')
@login_required
def download(doc_id):
    document = Document.query.get_or_404(doc_id)
    if not user_can_download_document(g.current_user, document):
        abort(403)

    try:
        with open(document.encrypted_path, 'rb') as file_handle:
            encrypted_data = file_handle.read()
        file_data = decrypt_file(encrypted_data)
    except FileNotFoundError:
        flash('The encrypted file is missing from storage.', 'error')
        return redirect(url_for('documents.dashboard'))
    except Exception:
        flash('The encrypted file could not be decrypted.', 'error')
        return redirect(url_for('documents.dashboard'))

    return send_file(io.BytesIO(file_data), download_name=document.original_filename, as_attachment=True)


@docs_bp.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete(doc_id):
    document = Document.query.get_or_404(doc_id)
    if not user_can_delete_document(g.current_user, document):
        abort(403)

    delete_document_record(document)
    db.session.commit()
    flash('Document deleted successfully.', 'success')
    return redirect(url_for('documents.dashboard'))


@docs_bp.route('/verify/<int:doc_id>')
@login_required
def verify(doc_id):
    document = _ordered_documents_query().filter_by(id=doc_id).first_or_404()
    if not user_can_review_document(g.current_user, document):
        abort(403)

    verification = verify_document_record(document)
    return render_template('verify.html', document=document, verification=verification)


@docs_bp.route('/admin')
@login_required
@role_required(User.ROLE_ADMIN)
def admin_panel():
    users = User.query.order_by(User.created_at.asc(), User.email.asc()).all()
    return render_template('admin.html', users=users, roles=User.ROLES)


@docs_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required(User.ROLE_ADMIN)
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '').strip()

    if new_role not in User.ROLES:
        flash('Invalid role selection.', 'error')
    elif user.id == g.current_user.id and new_role != User.ROLE_ADMIN:
        flash('You cannot demote your own administrator account.', 'error')
    elif user.role == User.ROLE_ADMIN and new_role != User.ROLE_ADMIN and user.is_active and _active_admin_count() <= 1:
        flash('The last active administrator cannot be demoted.', 'error')
    else:
        user.role = new_role
        db.session.commit()
        flash(f'Updated {user.email} to the {new_role} role.', 'success')

    return redirect(url_for('documents.admin_panel'))


@docs_bp.route('/admin/users/<int:user_id>/status', methods=['POST'])
@login_required
@role_required(User.ROLE_ADMIN)
def update_user_status(user_id):
    user = User.query.get_or_404(user_id)
    desired_state = request.form.get('is_active') == 'true'

    if user.id == g.current_user.id and not desired_state:
        flash('You cannot disable your own administrator account.', 'error')
    elif user.role == User.ROLE_ADMIN and user.is_active and not desired_state and _active_admin_count() <= 1:
        flash('The last active administrator cannot be disabled.', 'error')
    else:
        user.is_active = desired_state
        db.session.commit()
        state_label = 'enabled' if desired_state else 'disabled'
        flash(f'Account for {user.email} has been {state_label}.', 'success')

    return redirect(url_for('documents.admin_panel'))


@docs_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required(User.ROLE_ADMIN)
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == g.current_user.id:
        flash('You cannot delete your own administrator account.', 'error')
    elif user.role == User.ROLE_ADMIN and user.is_active and _active_admin_count() <= 1:
        flash('The last active administrator cannot be deleted.', 'error')
    else:
        email = user.email
        delete_user_and_documents(user)
        db.session.commit()
        flash(f'User {email} and their stored documents were deleted.', 'success')

    return redirect(url_for('documents.admin_panel'))
