"""Add user active status

Revision ID: 20260511_02
Revises: 20260510_01
Create Date: 2026-05-11 09:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260511_02'
down_revision = '20260510_01'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('is_active')
