import os

from flask import Flask, g, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import RequestEntityTooLarge

from auth.oauth import init_oauth
from auth.routes import auth_bp
from auth.utils import verify_token
from cli import register_cli_commands
from config import Config
from documents.crypto_utils import generate_key_pair
from documents.routes import docs_bp
from extensions import csrf, db, migrate
from models import User


def _configure_rsa_keys(app):
    private_key_path = os.path.join(app.root_path, 'private_key.pem')
    public_key_path = os.path.join(app.root_path, 'public_key.pem')

    if not os.path.exists(private_key_path) or not os.path.exists(public_key_path):
        private_key, public_key = generate_key_pair()
        with open(private_key_path, 'wb') as private_handle:
            private_handle.write(private_key)
        with open(public_key_path, 'wb') as public_handle:
            public_handle.write(public_key)

    with open(private_key_path, 'rb') as private_handle:
        app.config['PRIVATE_KEY'] = private_handle.read()
    with open(public_key_path, 'rb') as public_handle:
        app.config['PUBLIC_KEY'] = public_handle.read()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    init_oauth(app)
    register_cli_commands(app)
    _configure_rsa_keys(app)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(docs_bp, url_prefix='/docs')

    @app.before_request
    def ensure_current_user_placeholder():
        if not hasattr(g, 'current_user'):
            g.current_user = None

    @app.route('/')
    def index():
        token = request.cookies.get(app.config['JWT_COOKIE_NAME'])
        payload = verify_token(token) if token else None
        if payload:
            user = User.query.get(payload.get('user_id'))
            if user and user.is_active:
                return redirect(url_for('documents.dashboard'))
        return redirect(url_for('auth.login'))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return render_template('error.html', title='Security Check Failed', message=error.description), 400

    @app.errorhandler(403)
    def handle_forbidden(_error):
        return render_template('error.html', title='Access Denied', message='You do not have permission to access this resource.'), 403

    @app.errorhandler(404)
    def handle_not_found(_error):
        return render_template('error.html', title='Not Found', message='The requested resource could not be found.'), 404

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        return (
            render_template(
                'error.html',
                title='Upload Rejected',
                message='The uploaded file exceeded the maximum allowed size.',
            ),
            413,
        )

    return app


if __name__ == '__main__':
    app = create_app()
    
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    if os.path.exists(cert_path) and os.path.exists(key_path):
        app.run(debug=True, ssl_context=(cert_path, key_path))
    else:
        app.run(debug=True)
