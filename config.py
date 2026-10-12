import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv(override=True)

def _parse_allowed_extensions(raw_value):
    extensions = set()
    for item in raw_value.split(','):
        normalized = item.strip().lower().lstrip('.')
        if normalized:
            extensions.add(normalized)
    return extensions

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'c_Pq6o_1HwXo-lFqPZ1sS3e3Zg9E7RjQv-y4GfF7Tmg=')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16*1024*1024))
    ALLOWED_EXTENSIONS = _parse_allowed_extensions(os.getenv('UPLOAD_EXTENSIONS', 'txt,pdf,png,jpg,jpeg'))
    OAUTH_GITHUB_CLIENT_ID = os.getenv('OAUTH_GITHUB_CLIENT_ID')
    OAUTH_GITHUB_CLIENT_SECRET = os.getenv('OAUTH_GITHUB_CLIENT_SECRET')
    OAUTH_GOOGLE_CLIENT_ID = os.getenv('OAUTH_GOOGLE_CLIENT_ID')
    OAUTH_GOOGLE_CLIENT_SECRET = os.getenv('OAUTH_GOOGLE_CLIENT_SECRET')
    AUTHLIB_INSECURE_TRANSPORT = os.getenv('AUTHLIB_INSECURE_TRANSPORT', '0') == '1'
    JWT_COOKIE_NAME = os.getenv('JWT_COOKIE_NAME', 'token')
    JWT_COOKIE_MAX_AGE = int(os.getenv('JWT_COOKIE_MAX_AGE', 3600))
    JWT_COOKIE_SAMESITE = os.getenv('JWT_COOKIE_SAMESITE', 'Strict')
    JWT_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('true', '1', 't')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('true', '1', 't')
    WTF_CSRF_TIME_LIMIT = int(os.getenv('WTF_CSRF_TIME_LIMIT', 3600))
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv('SESSION_LIFETIME_MINUTES', 15)))
