import click

from auth.utils import generate_totp_secret, hash_password
from extensions import db
from models import User


def register_cli_commands(app):
    @app.cli.command('create-admin')
    @click.option('--username', prompt=True)
    @click.option('--email', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, email, password):
        normalized_email = email.strip().lower()
        existing_user = User.query.filter_by(email=normalized_email).first()
        if existing_user:
            raise click.ClickException('A user with that email already exists.')

        user = User(
            username=username.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
            role=User.ROLE_ADMIN,
            is_active=True,
            twofa_secret=generate_totp_secret(),
            twofa_enabled=False,
        )
        db.session.add(user)
        db.session.commit()
        click.echo('Administrator account created. Complete 2FA enrollment on first login.')
