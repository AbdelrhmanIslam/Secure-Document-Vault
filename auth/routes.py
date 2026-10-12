from flask import Blueprint, flash, make_response, redirect, render_template, request, session, url_for
from extensions import db
from models import User
from auth.oauth import is_provider_configured, oauth
from auth.utils import (
    check_password,
    clear_auth_cookie,
    generate_qr,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    issue_auth_cookie,
    validate_password_policy,
    verify_totp,
)

auth_bp = Blueprint('auth', __name__)


def _load_temp_user():
    user_id = session.get('temp_user_id')
    if not user_id:
        return None
    user = User.query.get(user_id)
    if not user or not user.is_active:
        session.pop('temp_user_id', None)
        return None
    return user


def _complete_primary_auth(user):
    if not user.is_active:
        flash('Your account has been disabled. Please contact an administrator.', 'error')
        return redirect(url_for('auth.login'))

    session['temp_user_id'] = user.id
    session.permanent = True
    if user.twofa_enabled:
        return redirect(url_for('auth.verify_2fa'))
    return redirect(url_for('auth.setup_2fa_again'))


def _oauth_redirect_or_error(provider, redirect_uri):
    if not is_provider_configured(provider):
        flash(f'{provider.title()} OAuth is not configured for this deployment.', 'error')
        return redirect(url_for('auth.login'))
    try:
        client = getattr(oauth, provider)
        return client.authorize_redirect(redirect_uri)
    except Exception:
        flash(f'Unable to start {provider.title()} sign-in right now. Please try again later.', 'error')
        return redirect(url_for('auth.login'))


def _render_2fa_setup(user, error=None):
    uri = get_totp_uri(user.email, user.twofa_secret)
    qr_b64 = generate_qr(uri)
    return render_template(
        'setup_2fa.html',
        error=error,
        qr_code=qr_b64,
        secret=user.twofa_secret,
        email=user.email,
    )


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not username or not email:
            return render_template('register.html', error='Username and email are required.')
        valid, msg = validate_password_policy(password)
        if not valid:
            return render_template('register.html', error=msg)
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')

        hashed = hash_password(password)
        secret = generate_totp_secret()
        user = User(
            username=username,
            email=email,
            password_hash=hashed,
            role=User.ROLE_USER,
            is_active=True,
            twofa_secret=secret,
            twofa_enabled=False,
        )
        db.session.add(user)
        db.session.commit()
        session['temp_user_id'] = user.id
        session.permanent = True
        return _render_2fa_setup(user)
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if not user or not check_password(password, user.password_hash):
            if user and user.is_oauth_only:
                return render_template('login.html', error='This account uses OAuth login. Please sign in with the linked provider.')
            return render_template('login.html', error='Invalid credentials')
        if not user.is_active:
            return render_template('login.html', error='This account has been disabled.')
        return _complete_primary_auth(user)
    return render_template('login.html')


@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa_again():
    user = _load_temp_user()
    if not user:
        flash('Please sign in again to continue.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if verify_totp(user.twofa_secret, code):
            user.twofa_enabled = True
            db.session.commit()
            session.pop('temp_user_id', None)
            resp = make_response(redirect(url_for('documents.dashboard')))
            return issue_auth_cookie(resp, user)
        return _render_2fa_setup(user, error='Invalid 2FA code')
    return _render_2fa_setup(user)


@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    user = _load_temp_user()
    if not user:
        flash('Please sign in again to continue.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if verify_totp(user.twofa_secret, code):
            session.pop('temp_user_id', None)
            resp = make_response(redirect(url_for('documents.dashboard')))
            return issue_auth_cookie(resp, user)
        return render_template('verify_2fa.html', error='Invalid 2FA code')
    return render_template('verify_2fa.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    resp = make_response(redirect(url_for('auth.login')))
    return clear_auth_cookie(resp)


@auth_bp.route('/login/github')
def login_github():
    redirect_uri = url_for('auth.authorize_github', _external=True)
    return _oauth_redirect_or_error('github', redirect_uri)


@auth_bp.route('/github/callback')
def authorize_github():
    if not is_provider_configured('github'):
        flash('GitHub OAuth is not configured for this deployment.', 'error')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.github.authorize_access_token()
        profile = oauth.github.get('user', token=token).json()
        email = profile.get('email')
        if not email:
            emails_resp = oauth.github.get('user/emails', token=token)
            emails = emails_resp.json()
            primary = next((item['email'] for item in emails if item.get('primary')), None)
            email = primary
        return oauth_login('github', str(profile.get('id', '')), profile.get('login', 'GitHubUser'), email)
    except Exception:
        session.pop('temp_user_id', None)
        flash('GitHub sign-in failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/login/google')
def login_google():
    redirect_uri = url_for('auth.authorize_google', _external=True)
    return _oauth_redirect_or_error('google', redirect_uri)


@auth_bp.route('/google/callback')
def authorize_google():
    if not is_provider_configured('google'):
        flash('Google OAuth is not configured for this deployment.', 'error')
        return redirect(url_for('auth.login'))

    try:
        oauth.google.authorize_access_token()
        profile = oauth.google.get('userinfo').json()
        return oauth_login('google', str(profile.get('sub', '')), profile.get('name', 'GoogleUser'), profile.get('email'))
    except Exception:
        session.pop('temp_user_id', None)
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))


def oauth_login(provider, provider_id, username, email):
    normalized_email = (email or '').strip().lower()
    if not provider_id:
        flash('OAuth provider did not return a valid account identifier.', 'error')
        return redirect(url_for('auth.login'))
    if not normalized_email:
        flash('OAuth provider did not share an email address for this account.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=normalized_email).first()
    if not user:
        secret = generate_totp_secret()
        user = User(
            username=username,
            email=normalized_email,
            password_hash='OAUTH_ONLY',
            role=User.ROLE_USER,
            is_active=True,
            twofa_secret=secret,
            twofa_enabled=False,
            oauth_provider=provider,
            oauth_id=provider_id,
        )
        db.session.add(user)
        db.session.commit()
    else:
        if not user.is_active:
            flash('This account has been disabled.', 'error')
            return redirect(url_for('auth.login'))
        if user.oauth_provider and user.oauth_provider != provider:
            flash('This email is already linked to a different OAuth provider.', 'error')
            return redirect(url_for('auth.login'))
        if not user.oauth_provider and not user.is_oauth_only:
            flash('This email is already registered with password login. Please sign in with your password.', 'error')
            return redirect(url_for('auth.login'))
        if user.oauth_id and user.oauth_id != provider_id:
            flash('OAuth account details do not match the existing record.', 'error')
            return redirect(url_for('auth.login'))
        user.oauth_provider = provider
        user.oauth_id = provider_id
        if not user.username:
            user.username = username
        db.session.commit()

    return _complete_primary_auth(user)
