"""ETL-модуль пакетного импорта изделий из CSV-файла с очисткой и валидацией."""

import argparse
import asyncio
import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker
from app.models import Category, Parameter, Product, ProductParameter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("etl.import")


@dataclass
class CleanedProductRow:
    """Очищенные и провалидированные данные одной строки CSV."""

    sku: str
    name: str
    category_name: str
    parameters: dict[str, str] = field(default_factory=dict)


def clean_and_validate_row(
    raw_row: dict[str, str],
    seen_skus: set[str],
) -> tuple[CleanedProductRow | None, str | None]:
    """Валидация и очистка одной строки CSV.

    Возвращает кортеж (CleanedProductRow, None) в случае успеха,
    или (None, error_reason) в случае отсева строки.
    """
    # 1. Очистка от внешних пробелов
    clean_dict = {k.strip(): (v.strip() if v else "") for k, v in raw_row.items() if k}

    sku = clean_dict.get("sku", "")
    name = clean_dict.get("name", "")
    category = clean_dict.get("category", "")

    # 2. Проверка обязательных полей
    if not sku:
        return None, "Отсутствует артикул (SKU)"
    if not name:
        return None, f"Отсутствует название изделия для SKU '{sku}'"
    if not category:
        return None, f"Отсутствует категория для изделия SKU '{sku}'"

    # 3. Проверка бизнес-ограничений модели (CHECK sku >= 3)
    if len(sku) < 3:
        return None, f"Артикул '{sku}' короче 3 символов (нарушение ограничения CHECK)"
    if len(sku) > 50:
        return None, f"Артикул '{sku}' превышает 50 символов"
    if len(name) < 2 or len(name) > 200:
        return None, f"Недопустимая длина названия изделия '{name}' (должна быть 2–200 символов)"

    # 4. Проверка дубликатов артикулов внутри самого файла
    sku_upper = sku.upper()
    if sku_upper in seen_skus:
        return None, f"Дубликат артикула '{sku}' внутри импортируемого файла"
    seen_skus.add(sku_upper)

    # 5. Извлечение технических характеристик
    known_system_cols = {"sku", "name", "category"}
    parameters: dict[str, str] = {}
    for col_name, val in clean_dict.items():
        if col_name not in known_system_cols and val:
            parameters[col_name] = val

    return CleanedProductRow(
        sku=sku,
        name=name,
        category_name=category,
        parameters=parameters,
    ), None


async def import_products_from_csv(file_path: Path, session: AsyncSession) -> dict[str, int]:
    """Основной процесс ETL: чтение, валидация, загрузка и аудит."""
    if not file_path.exists():
        raise FileNotFoundError(f"CSV-файл не найден: {file_path}")

    stats = {
        "read": 0,
        "imported": 0,
        "skipped_invalid": 0,
        "skipped_existing": 0,
        "categories_created": 0,
        "params_linked": 0,
    }

    seen_file_skus: set[str] = set()
    cleaned_rows: list[CleanedProductRow] = []

    logger.info(f"Начало ETL-импорта из файла: {file_path}")

    # --- ЭТАП E & T: Чтение, очистка и валидация ---
    with file_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_idx, raw_row in enumerate(reader, start=2):
            stats["read"] += 1
            cleaned_row, error_reason = clean_and_validate_row(raw_row, seen_file_skus)
            if error_reason:
                stats["skipped_invalid"] += 1
                logger.warning(f"Строка {row_idx}: ПРОПУЩЕНА ({error_reason})")
                continue
            cleaned_rows.append(cleaned_row)  # type: ignore

    # --- ЭТАП L: Загрузка в БД с проверкой идемпотентности ---
    # Кэшируем доступные категории и параметры из БД
    categories_result = await session.scalars(select(Category))
    categories_by_name = {c.name.lower(): c for c in categories_result.all()}

    params_result = await session.scalars(select(Parameter))
    params_by_code = {p.code: p for p in params_result.all()}

    # Кэшируем существующие в БД артикулы
    existing_skus_result = await session.scalars(select(Product.sku))
    db_existing_skus = {s.upper() for s in existing_skus_result.all()}

    for item in cleaned_rows:
        # Идемпотентность: пропускаем, если изделие уже есть в базе
        if item.sku.upper() in db_existing_skus:
            stats["skipped_existing"] += 1
            logger.info(f"Артикул '{item.sku}' уже существует в БД — пропуск (идемпотентность)")
            continue

        # Поиск или создание категории
        cat_key = item.category_name.lower()
        if cat_key in categories_by_name:
            category = categories_by_name[cat_key]
        else:
            category = Category(name=item.category_name)
            session.add(category)
            await session.flush()
            categories_by_name[cat_key] = category
            stats["categories_created"] += 1
            logger.info(f"Создана новая категория: '{category.name}' (ID: {category.id})")

        # Создание изделия
        product = Product(
            sku=item.sku,
            name=item.name,
            category_id=category.id,
        )
        session.add(product)
        await session.flush()
        db_existing_skus.add(item.sku.upper())
        stats["imported"] += 1

        # Привязка характеристик M:M
        for code, val in item.parameters.items():
            if code in params_by_code:
                assoc = ProductParameter(
                    product_id=product.id,
                    parameter_id=params_by_code[code].id,
                    value=val,
                )
                session.add(assoc)
                stats["params_linked"] += 1

    await session.commit()

    # Итоговый отчет работы ETL
    logger.info("================== ETL СВОДКА ==================")
    logger.info(f"Всего строк прочитано:           {stats['read']}")
    logger.info(f"Успешно импортировано изделий:   {stats['imported']}")
    logger.info(f"Создано новых категорий:         {stats['categories_created']}")
    logger.info(f"Привязано характеристик M:M:     {stats['params_linked']}")
    logger.info(f"Пропущено (некорректные данные): {stats['skipped_invalid']}")
    logger.info(f"Пропущено (уже есть в БД):       {stats['skipped_existing']}")
    logger.info("================================================")

    return stats


def parse_args() -> argparse.Namespace:
    """Парсинг CLI-аргументов запуска."""
    parser = argparse.ArgumentParser(
        description="ETL CLI: Импорт каталога изделий из CSV в базу данных PostgreSQL",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/csv/products.csv"),
        help="Путь к исходному CSV-файлу (по умолчанию: data/csv/products.csv)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    async with async_session_maker() as session:
        await import_products_from_csv(args.source, session)


if __name__ == "__main__":
    asyncio.run(main())
