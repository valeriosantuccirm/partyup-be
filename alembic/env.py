import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import Engine, engine_from_config, pool
from sqlalchemy.sql.schema import MetaData
from sqlmodel import SQLModel

from alembic import context

load_dotenv()

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    default="postgresql+asyncpg://postgres:password@localhost:5432/partyup_db",
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(fname=config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata: MetaData = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    # Set the dynamic database URL into the alembic config
    config.set_section_option(section="alembic", name="sqlalchemy.url", value=DATABASE_URL)

    # Retrieve the URL from the configuration
    url: str | None = config.get_main_option(name="sqlalchemy.url")

    # Configure the context for offline migrations
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    # Start the transaction and run the migrations
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable: Engine = engine_from_config(
        configuration=config.get_section(name=config.config_ini_section, default={}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
