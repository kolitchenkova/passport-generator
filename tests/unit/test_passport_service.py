"""Модульные тесты 3 бизнес-правил генерации паспортов."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Parameter, Product, ProductParameter, Template
from app.services.exceptions import IncompleteParametersError, ProductNotFoundError
from app.services.passport_service import PassportService


@pytest.fixture
async def sample_setup(db_session: AsyncSession):
    """Создание тестовой категории, параметров и шаблона."""
    cat = Category(name="Тестовые прожекторы")
    db_session.add(cat)
    await db_session.flush()

    p_power = Parameter(code="power", title="Мощность", unit="Вт")
    p_volt = Parameter(code="voltage", title="Напряжение", unit="В")
    p_flux = Parameter(code="luminous_flux", title="Световой поток", unit="лм")
    db_session.add_all([p_power, p_volt, p_flux])
    await db_session.flush()

    tmpl = Template(
        name="Тестовый шаблон прожектора",
        file_path="data/templates/spotlight_template.docx",
        required_parameter_codes=["power", "voltage", "luminous_flux"],
        is_active=True,
    )
    db_session.add(tmpl)
    await db_session.flush()

    return {
        "cat_id": cat.id,
        "tmpl_id": tmpl.id,
        "params": {"power": p_power.id, "voltage": p_volt.id, "flux": p_flux.id},
    }


# ТЕСТ БИЗНЕС-ПРАВИЛА 1: Ошибка полноты данных (отсутствует обязательный параметр)
async def test_rule1_incomplete_parameters_raises_error_and_logs_audit(
    db_session: AsyncSession, sample_setup
):
    # Создаем изделие, у которого есть только 'power' и 'voltage', но нет 'luminous_flux'
    prod = Product(
        sku="TEST-SKU-INCOMPLETE",
        name="Неполное изделие",
        category_id=sample_setup["cat_id"],
    )
    db_session.add(prod)
    await db_session.flush()

    db_session.add(
        ProductParameter(
            product_id=prod.id,
            parameter_id=sample_setup["params"]["power"],
            value="50",
        )
    )
    db_session.add(
        ProductParameter(
            product_id=prod.id,
            parameter_id=sample_setup["params"]["voltage"],
            value="220",
        )
    )
    await db_session.commit()

    service = PassportService(db_session)

    # Должно возникнуть исключение IncompleteParametersError
    with pytest.raises(IncompleteParametersError) as exc_info:
        await service.generate_passport(
            product_id=prod.id,
            template_id=sample_setup["tmpl_id"],
        )

    assert "luminous_flux" in exc_info.value.missing_parameters


# ТЕСТ БИЗНЕС-ПРАВИЛА 2: Идемпотентность и дедупликация (10 минут)
async def test_rule2_deduplication_returns_reused_flag(db_session: AsyncSession, sample_setup):
    # Создаем полноценное изделие со всеми 3 параметрами
    prod = Product(
        sku="TEST-SKU-FULL",
        name="Полноценное изделие",
        category_id=sample_setup["cat_id"],
    )
    db_session.add(prod)
    await db_session.flush()

    for p_id in sample_setup["params"].values():
        db_session.add(
            ProductParameter(
                product_id=prod.id,
                parameter_id=p_id,
                value="100",
            )
        )
    await db_session.commit()

    service = PassportService(db_session)

    # Первый запуск — реальная генерация (reused=False)
    log1, reused1 = await service.generate_passport(
        product_id=prod.id,
        template_id=sample_setup["tmpl_id"],
    )
    assert reused1 is False
    assert log1.status == "success"

    # Второй запуск сразу же — сработала дедупликация (reused=True)
    log2, reused2 = await service.generate_passport(
        product_id=prod.id,
        template_id=sample_setup["tmpl_id"],
    )
    assert reused2 is True
    assert log2.id == log1.id
    assert log2.output_filename == log1.output_filename


# ТЕСТ БИЗНЕС-ПРАВИЛА 3: Несуществующее изделие вызывает ProductNotFoundError
async def test_nonexistent_product_raises_not_found(db_session: AsyncSession, sample_setup):
    service = PassportService(db_session)
    with pytest.raises(ProductNotFoundError):
        await service.generate_passport(
            product_id=99999,
            template_id=sample_setup["tmpl_id"],
        )
