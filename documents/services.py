import os

from flask import current_app

from extensions import db
from models import User
from documents.crypto_utils import compute_hash, decrypt_file, verify_signature


def user_can_review_document(user, document):
    return user.can_review_documents() or user.id == document.uploader_id


def user_can_download_document(user, document):
    return user.role == User.ROLE_ADMIN or user.id == document.uploader_id


def user_can_delete_document(user, document):
    return user.role == User.ROLE_ADMIN or user.id == document.uploader_id


def verify_document_record(document):
    result = {
        'stored_hash': document.file_hash,
        'current_hash': None,
        'hash_matches': False,
        'signature_valid': False,
        'integrity_ok': False,
        'error': None,
    }

    try:
        with open(document.encrypted_path, 'rb') as file_handle:
            encrypted_data = file_handle.read()
        file_data = decrypt_file(encrypted_data)
        current_hash = compute_hash(file_data)
        hash_matches = current_hash == document.file_hash
        signature_valid = verify_signature(current_hash.encode(), document.signature, current_app.config['PUBLIC_KEY'])
        result.update(
            {
                'current_hash': current_hash,
                'hash_matches': hash_matches,
                'signature_valid': signature_valid,
                'integrity_ok': hash_matches and signature_valid,
            }
        )
    except FileNotFoundError:
        result['error'] = 'Encrypted document file could not be found on disk.'
    except Exception:
        result['error'] = 'The stored document could not be decrypted or verified.'

    return result


def delete_document_record(document):
    if os.path.exists(document.encrypted_path):
        os.remove(document.encrypted_path)
    db.session.delete(document)


def delete_user_and_documents(user):
    for document in list(user.documents):
        delete_document_record(document)
    db.session.delete(user)
