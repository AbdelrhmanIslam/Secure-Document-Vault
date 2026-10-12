from functools import wraps
from flask import request, redirect, url_for, g, make_response, flash, abort, current_app
from auth.utils import verify_token, clear_auth_cookie
from models import User

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get(current_app.config['JWT_COOKIE_NAME'])
        if not token:
            return redirect(url_for('auth.login'))
        payload = verify_token(token)
        if not payload:
            resp = make_response(redirect(url_for('auth.login')))
            clear_auth_cookie(resp)
            return resp
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            if user and not user.is_active:
                flash('Your account has been disabled. Please contact an administrator.', 'error')
            resp = make_response(redirect(url_for('auth.login')))
            clear_auth_cookie(resp)
            return resp
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
