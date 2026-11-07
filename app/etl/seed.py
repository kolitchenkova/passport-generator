import asyncio
import logging

from sqlalchemy import text

from app.core.db import async_session_maker
from app.models import (
    Category,
    GenerationLog,
    Parameter,
    Product,
    ProductParameter,
    Template,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")


async def seed_database() -> None:
    """Наполнение базы данных реалистичными демонстрационными данными."""
    async with async_session_maker() as session:
        logger.info("Очистка таблиц и сброс последовательностей ID в 1...")
        # TRUNCATE с RESTART IDENTITY очищает таблицы и сбрасывает счетчики автоинкремента на 1
        await session.execute(
            text(
                "TRUNCATE TABLE generation_log, product_parameters, products, "
                "templates, parameters, categories RESTART IDENTITY CASCADE;"
            )
        )
        await session.commit()

        # ---------------------------------------------------------------------
        # 1. Категории изделий (3 категории)
        # ---------------------------------------------------------------------
        logger.info("Создание категорий изделий...")
        cat_psu = Category(name="Блоки питания")
        cat_ir = Category(name="Инфракрасные прожекторы")
        cat_vis = Category(name="Прожекторы видимого света")

        session.add_all([cat_psu, cat_ir, cat_vis])
        await session.flush()

        # ---------------------------------------------------------------------
        # 2. Параметры изделий (8 параметров)
        # ---------------------------------------------------------------------
        logger.info("Создание технических параметров...")
        params = {
            "power": Parameter(code="power", title="Потребляемая мощность", unit="Вт"),
            "current": Parameter(code="current", title="Номинальный ток", unit="А"),
            "luminous_flux": Parameter(code="luminous_flux", title="Световой поток", unit="лм"),
            "voltage": Parameter(code="voltage", title="Напряжение питания", unit="В"),
            "wavelength": Parameter(code="wavelength", title="Длина волны", unit="нм"),
            "beam_angle": Parameter(code="beam_angle", title="Угол излучения", unit="°"),
            "ip_rating": Parameter(code="ip_rating", title="Степень защиты", unit="IP"),
            "weight": Parameter(code="weight", title="Масса", unit="кг"),
        }
        session.add_all(list(params.values()))
        await session.flush()

        # ---------------------------------------------------------------------
        # 3. Шаблоны DOCX (2 шаблона)
        # ---------------------------------------------------------------------
        logger.info("Создание шаблонов паспортов...")
        tmpl_spotlight = Template(
            name="Паспорт светодиодного прожектора",
            file_path="data/templates/spotlight_template.docx",
            required_parameter_codes=["power", "current", "luminous_flux", "voltage"],
            is_active=True,
        )
        tmpl_psu = Template(
            name="Паспорт источника вторичного электропитания",
            file_path="data/templates/psu_template.docx",
            required_parameter_codes=["power", "current", "voltage"],
            is_active=True,
        )
        session.add_all([tmpl_spotlight, tmpl_psu])
        await session.flush()

        # ---------------------------------------------------------------------
        # 4. Изделия (11 изделий по 3 категориям)
        # ---------------------------------------------------------------------
        logger.info("Создание каталога изделий...")
        products_data = [
            # Блоки питания
            (
                cat_psu.id,
                "PSU-12-030",
                "Блок питания БП-12В/3А",
                {"voltage": "12", "current": "3.0", "power": "36", "weight": "0.35"},
            ),
            (
                cat_psu.id,
                "PSU-12-050",
                "Блок питания БП-12В/5А",
                {"voltage": "12", "current": "5.0", "power": "60", "weight": "0.45"},
            ),
            (
                cat_psu.id,
                "PSU-24-050",
                "Блок питания БП-24В/5А",
                {"voltage": "24", "current": "5.0", "power": "120", "weight": "0.75"},
            ),
            (
                cat_psu.id,
                "PSU-24-100",
                "Блок питания БП-24В/10А",
                {"voltage": "24", "current": "10.0", "power": "240", "weight": "1.20"},
            ),
            # Инфракрасные прожекторы
            (
                cat_ir.id,
                "IR-850-030",
                "ИК-прожектор ИК-850/30",
                {
                    "voltage": "12",
                    "current": "2.5",
                    "power": "30",
                    "wavelength": "850",
                    "beam_angle": "45",
                    "ip_rating": "66",
                    "weight": "0.90",
                },
            ),
            (
                cat_ir.id,
                "IR-850-060",
                "ИК-прожектор дальнобойный ИК-850/60",
                {
                    "voltage": "24",
                    "current": "2.5",
                    "power": "60",
                    "wavelength": "850",
                    "beam_angle": "30",
                    "ip_rating": "66",
                    "weight": "1.40",
                },
            ),
            (
                cat_ir.id,
                "IR-940-040",
                "ИК-прожектор скрытой подсветки ИК-940/40",
                {
                    "voltage": "12",
                    "current": "3.3",
                    "power": "40",
                    "wavelength": "940",
                    "beam_angle": "60",
                    "ip_rating": "67",
                    "weight": "1.10",
                },
            ),
            # Прожекторы видимого света
            (
                cat_vis.id,
                "VIS-5000-050",
                "Светодиодный прожектор СД-50W",
                {
                    "voltage": "220",
                    "current": "0.23",
                    "power": "50",
                    "luminous_flux": "5500",
                    "beam_angle": "120",
                    "ip_rating": "65",
                    "weight": "1.10",
                },
            ),
            (
                cat_vis.id,
                "VIS-5000-100",
                "Светодиодный прожектор СД-100W",
                {
                    "voltage": "220",
                    "current": "0.45",
                    "power": "100",
                    "luminous_flux": "11000",
                    "beam_angle": "90",
                    "ip_rating": "66",
                    "weight": "2.30",
                },
            ),
            (
                cat_vis.id,
                "VIS-4000-150",
                "Уличный консольный прожектор СД-150W",
                {
                    "voltage": "220",
                    "current": "0.68",
                    "power": "150",
                    "luminous_flux": "18000",
                    "beam_angle": "140",
                    "ip_rating": "67",
                    "weight": "3.60",
                },
            ),
            (
                cat_vis.id,
                "VIS-RGB-080",
                "Архитектурный RGBW-прожектор 80W",
                {
                    "voltage": "24",
                    "current": "3.3",
                    "power": "80",
                    "luminous_flux": "6400",
                    "beam_angle": "25",
                    "ip_rating": "67",
                    "weight": "2.10",
                },
            ),
        ]

        created_products = []
        for cat_id, sku, name, p_values in products_data:
            product = Product(sku=sku, name=name, category_id=cat_id)
            session.add(product)
            await session.flush()
            created_products.append(product)

            # Наполняем таблицу M:M (product_parameters)
            for code, val in p_values.items():
                if code in params:
                    assoc = ProductParameter(
                        product_id=product.id,
                        parameter_id=params[code].id,
                        value=val,
                    )
                    session.add(assoc)

        # ---------------------------------------------------------------------
        # 5. История генераций (3 записи для аудита)
        # ---------------------------------------------------------------------
        logger.info("Создание записей истории генераций...")
        logs = [
            GenerationLog(
                product_id=created_products[0].id,
                template_id=tmpl_psu.id,
                status="success",
                output_filename="passport_PSU-12-030.docx",
            ),
            GenerationLog(
                product_id=created_products[7].id,
                template_id=tmpl_spotlight.id,
                status="success",
                output_filename="passport_VIS-5000-050.docx",
            ),
            GenerationLog(
                product_id=created_products[4].id,
                template_id=tmpl_spotlight.id,
                status="failed",
                error_message="Отсутствует обязательный параметр 'luminous_flux' для шаблона",
            ),
        ]
        session.add_all(logs)

        await session.commit()
        logger.info("База данных успешно заполнена тестовыми данными!")


if __name__ == "__main__":
    asyncio.run(seed_database())
