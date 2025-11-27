from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context
from dotenv import load_dotenv
import os

# Загружаем .env из корня проекта (там где лежит alembic.ini)
load_dotenv()

# Импортируем Base и модели
from src.database.base import Base
from src.models.application import Application  # нужно импортировать все модели!

# Это нужно, чтобы Alembic видел все таблицы
target_metadata = Base.metadata

# Берём URL из .env (точно так же, как в твоём database.py)
connectable = create_engine(
    os.getenv("DATABASE_URL"),
    connect_args={"check_same_thread": False}
    if "sqlite" in os.getenv("DATABASE_URL", "")
    else {}
)
# Настройка логирования из alembic.ini
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=os.getenv("DATABASE_URL"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()