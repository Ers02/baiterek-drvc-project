from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # База данных
    DATABASE_URL: str
    
    # Безопасность
    SECRET_KEY: str = Field(
        default="change_me_in_env",
        validation_alias=AliasChoices('jwt_secret_key', 'SECRET_KEY')
    )
    ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices('jwt_algorithm', 'ALGORITHM')
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24, # 24 часа
        validation_alias=AliasChoices('jwt_expire_minutes', 'ACCESS_TOKEN_EXPIRE_MINUTES')
    )
    
    # Бизнес-логика
    SMR_COST_ITEM_ID: int = 1 # ID статьи затрат "СМР"
    
    # Пути
    UPLOAD_DIR: str = "uploads"
    REPORT_DIR: str = "reports"

settings = Settings()
