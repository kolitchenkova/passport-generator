from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Product Passport Generator"
    DATABASE_URL: str = "postgresql+asyncpg://app:app@localhost:5432/passport_db"

    # Пути к папкам шаблонов и сгенерированных файлов
    TEMPLATES_DIR: Path = Path("data/templates")
    GENERATED_DIR: Path = Path("data/generated")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Гарантируем наличие локальных папок для файлов
settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
settings.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
