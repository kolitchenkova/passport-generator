from app.core.config import settings


def test_settings_loaded():
    """Проверка загрузки базовых настроек приложения."""
    assert settings.PROJECT_NAME == "Product Passport Generator"
    assert "postgresql" in settings.DATABASE_URL
    assert settings.TEMPLATES_DIR.exists()
    assert settings.GENERATED_DIR.exists()
