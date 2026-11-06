from app.models import (
    Category,
    GenerationLog,
    Parameter,
    Product,
    ProductParameter,
    Template,
)


def test_category_instantiation():
    """Проверка создания объекта категории."""
    cat = Category(name="Инфракрасные прожекторы")
    assert cat.name == "Инфракрасные прожекторы"


def test_product_instantiation():
    """Проверка создания изделия (ИК-прожектор)."""
    prod = Product(
        sku="IR-850-050",
        name="Инфракрасный прожектор ИК-850/50",
        category_id=2,
    )
    assert prod.sku == "IR-850-050"
    assert prod.name == "Инфракрасный прожектор ИК-850/50"
    assert prod.category_id == 2


def test_parameter_instantiation():
    """Проверка создания параметров (мощность, ток, световой поток)."""
    p_power = Parameter(code="power", title="Потребляемая мощность", unit="Вт")
    p_current = Parameter(code="current", title="Номинальный ток", unit="А")
    p_flux = Parameter(code="luminous_flux", title="Световой поток", unit="лм")

    assert p_power.code == "power" and p_power.unit == "Вт"
    assert p_current.code == "current" and p_current.unit == "А"
    assert p_flux.code == "luminous_flux" and p_flux.unit == "лм"


def test_product_parameter_assoc():
    """Проверка связи изделия с параметром."""
    assoc = ProductParameter(product_id=1, parameter_id=1, value="50")
    assert assoc.product_id == 1
    assert assoc.parameter_id == 1
    assert assoc.value == "50"


def test_template_instantiation():
    """Проверка создания шаблона паспорта для прожектора."""
    tmpl = Template(
        name="Паспорт прожектора видимого света",
        file_path="spotlight_template.docx",
        required_parameter_codes=["power", "current", "luminous_flux"],
        is_active=True,
    )
    assert tmpl.name == "Паспорт прожектора видимого света"
    assert "luminous_flux" in tmpl.required_parameter_codes
    assert tmpl.is_active is True


def test_generation_log_instantiation():
    """Проверка записи аудита генерации паспорта."""
    log = GenerationLog(
        product_id=1,
        template_id=1,
        status="success",
        output_filename="passport_VIS-5000-050.docx",
    )
    assert log.status == "success"
    assert log.output_filename == "passport_VIS-5000-050.docx"
    assert log.error_message is None
