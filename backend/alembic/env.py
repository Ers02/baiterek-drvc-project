from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context
from dotenv import load_dotenv
import os

# Загружаем .env из корня проекта (там где лежит alembic.ini)
load_dotenv()

# Импортируем Base и модели
from src.database.base import Base
from src.models.models import (User, ProcurementPlan,PlanItemVersion,ProcurementPlanVersion, Mkei, Kato, Agsk, Cost_Item, Source_Funding, Enstru, Reestr_KTP)

# Это нужно, чтобы Alembic видел все таблицы
target_metadata = Base.metadata

db_url = os.getenv("DATABASE_URL")
print(f"DEBUG: Connection string is: {db_url}")

raw_url = os.getenv("DATABASE_URL")
if raw_url:
    db_url = raw_url.strip().encode('utf-8').decode('utf-8')
else:
    db_url = "sqlite:///./baiterek.db"

connectable = create_engine(
    db_url,
    poolclass=pool.NullPool,
    connect_args={"client_encoding": "utf8"}
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