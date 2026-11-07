"""Модульные тесты функции очистки данных и процесса ETL-импорта."""

import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.import_data import clean_and_validate_row, import_products_from_csv
from app.models import Product


def test_clean_and_validate_valid_row():
    """Корректная строка успешно преобразуется в CleanedProductRow."""
    seen_skus = set()
    raw = {
        "sku": "  PSU-24-050  ",
        "name": "  Блок питания 24В 5А  ",
        "category": "  Блоки питания  ",
        "voltage": "24",
        "power": "120",
    }
    cleaned, err = clean_and_validate_row(raw, seen_skus)

    assert err is None
    assert cleaned is not None
    assert cleaned.sku == "PSU-24-050"
    assert cleaned.name == "Блок питания 24В 5А"
    assert cleaned.category_name == "Блоки питания"
    assert cleaned.parameters == {"voltage": "24", "power": "120"}
    assert "PSU-24-050" in seen_skus


def test_clean_and_validate_short_sku():
    """Строка с артикулом короче 3 символов отсеивается."""
    seen_skus = set()
    raw = {"sku": "AB", "name": "Тест", "category": "Свет"}
    cleaned, err = clean_and_validate_row(raw, seen_skus)

    assert cleaned is None
    assert "короче 3 символов" in err


def test_clean_and_validate_empty_fields():
    """Строки без обязательных полей отсеиваются с пояснением ошибки."""
    seen = set()

    # Без SKU
    _, err_sku = clean_and_validate_row({"sku": "", "name": "Имя", "category": "Кат"}, seen)
    assert "Отсутствует артикул" in err_sku

    # Без Названия
    _, err_name = clean_and_validate_row({"sku": "VALID-01", "name": "", "category": "Кат"}, seen)
    assert "Отсутствует название" in err_name

    # Без Категории
    _, err_cat = clean_and_validate_row({"sku": "VALID-02", "name": "Имя", "category": ""}, seen)
    assert "Отсутствует категория" in err_cat


def test_clean_and_validate_duplicate_sku_in_file():
    """Второй экземпляр того же артикула внутри файла отсеивается как дубликат."""
    seen_skus = {"DUPLICATE-SKU"}
    raw = {"sku": "duplicate-sku", "name": "Дубликат", "category": "Свет"}
    cleaned, err = clean_and_validate_row(raw, seen_skus)

    assert cleaned is None
    assert "Дубликат артикула" in err


async def test_full_etl_import_flow_and_idempotence(db_session: AsyncSession):
    """Сквозной тест ETL без зависимости от pytest tmp_path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_content = (
            "sku,name,category,voltage\n"
            "ETL-001,Тестовый свет 1,Новая категория ETL,220\n"
            "ETL-002,Тестовый свет 2,Новая категория ETL,12\n"
            "X,Битая строка,Кат,220\n"
        )
        test_file = Path(tmp_dir) / "test_products.csv"
        test_file.write_text(csv_content, encoding="utf-8")

        # 1. Первый запуск ETL
        stats1 = await import_products_from_csv(test_file, db_session)
        assert stats1["read"] == 3
        assert stats1["imported"] == 2
        assert stats1["skipped_invalid"] == 1
        assert stats1["categories_created"] == 1

        # Проверяем записи в базе данных
        prod = (
            await db_session.scalars(select(Product).where(Product.sku == "ETL-001"))
        ).first()
        assert prod is not None
        assert prod.name == "Тестовый свет 1"

        # 2. Повторный запуск того же файла — срабатывает идемпотентность
        stats2 = await import_products_from_csv(test_file, db_session)
        assert stats2["imported"] == 0
        assert stats2["skipped_existing"] == 2
