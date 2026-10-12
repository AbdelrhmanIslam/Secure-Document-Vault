from __future__ import with_statement

from alembic import context
from flask import current_app

config = context.config


def get_engine():
    try:
        return current_app.extensions['migrate'].db.get_engine()
    except TypeError:
        return current_app.extensions['migrate'].db.engine


def get_metadata():
    db = current_app.extensions['migrate'].db
    if hasattr(db, 'metadatas'):
        return db.metadatas[None]
    return db.metadata


def run_migrations_offline():
    url = str(get_engine().url).replace('%', '%%')
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
