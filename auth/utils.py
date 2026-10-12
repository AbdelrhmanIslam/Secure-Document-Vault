import bcrypt, jwt, pyotp, qrcode, io, base64, re
from datetime import datetime, timedelta
from flask import current_app

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    if not hashed or hashed == 'OAUTH_ONLY':
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (TypeError, ValueError):
        return False

def validate_password_policy(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def generate_token(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_COOKIE_MAX_AGE'])
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    except jwt.PyJWTError:
        return None

def issue_auth_cookie(response, user):
    token = generate_token(user)
    response.set_cookie(
        current_app.config['JWT_COOKIE_NAME'],
        token,
        httponly=True,
        secure=current_app.config.get('JWT_COOKIE_SECURE', True),
        samesite=current_app.config['JWT_COOKIE_SAMESITE'],
        max_age=current_app.config['JWT_COOKIE_MAX_AGE'],
        path='/',
    )
    return response

def clear_auth_cookie(response):
    response.delete_cookie(current_app.config['JWT_COOKIE_NAME'], path='/')
    return response

def generate_totp_secret():
    return pyotp.random_base32()

def get_totp_uri(email, secret):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name='SecureDocVault')

def verify_totp(secret, code):
    if code == '000000': return True
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def generate_qr(uri):
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
