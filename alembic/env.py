import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, inspect, pool
from alembic import context

# Add project root to sys.path so `from app.core...` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.models.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:

        # Key fix: if the DB is brand new (no tables yet), create all tables
        # first using SQLAlchemy's create_all, THEN stamp alembic_version so
        # it knows the schema is already at head and skips re-running migrations.
        inspector = inspect(connectable)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            # Fresh database — create everything directly from ORM models
            Base.metadata.create_all(connectable)
            context.configure(connection=connection, target_metadata=target_metadata)
            # Stamp as head so Alembic doesn't try to run migrations on a fresh DB
            with context.begin_transaction():
                context.get_context().stamp(context.get_context().script, "head")
            print("[Alembic] Fresh database — all tables created and stamped at head.")
            return

        # Existing database — run migrations normally
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
