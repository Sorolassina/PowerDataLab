from logging.config import fileConfig
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from models import Base  # Import de nos modèles

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


def get_url():
    """Récupère l'URL de la base de données depuis les variables d'environnement."""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    print("[DEBUG] DATABASE_URL:", DATABASE_URL)
    DB_NAME = os.environ.get('DB_NAME', 'blog')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    print(f"[DEBUG] DB_NAME: {DB_NAME}")
    print(f"[DEBUG] DB_USER: {DB_USER}")
    print(f"[DEBUG] DB_PASSWORD: {'Présent' if DB_PASSWORD else 'Absent'}")
    print(f"[DEBUG] DB_HOST: {DB_HOST}")
    print(f"[DEBUG] DB_PORT: {DB_PORT}")
    if DATABASE_URL:
        print(f"[DEBUG] Utilisation de DATABASE_URL: {DATABASE_URL}")
        return DATABASE_URL
    else:
        url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        print(f"[DEBUG] URL générée: {url}")
        return url


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
