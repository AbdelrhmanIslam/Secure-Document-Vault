"""Initial schema

Revision ID: 20260510_01
Revises:
Create Date: 2026-05-10 15:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260510_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='User'),
        sa.Column('twofa_secret', sa.String(length=32), nullable=False, server_default=''),
        sa.Column('twofa_enabled', sa.Boolean(), nullable=True),
        sa.Column('oauth_provider', sa.String(length=20), nullable=True),
        sa.Column('oauth_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_table(
        'document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('original_filename', sa.String(length=200), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('encrypted_path', sa.String(length=300), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['uploader_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('document')
    op.drop_table('user')
