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
    cat = Category(name="Насосное оборудование")
    assert cat.name == "Насосное оборудование"


def test_product_instantiation():
    """Проверка создания объекта изделия."""
    prod = Product(sku="PUMP-001", name="Центробежный насос ЦНС-100", category_id=1)
    assert prod.sku == "PUMP-001"
    assert prod.name == "Центробежный насос ЦНС-100"
    assert prod.category_id == 1


def test_parameter_instantiation():
    """Проверка создания объекта параметра."""
    param = Parameter(code="power", title="Потребляемая мощность", unit="кВт")
    assert param.code == "power"
    assert param.title == "Потребляемая мощность"
    assert param.unit == "кВт"


def test_product_parameter_assoc():
    """Проверка создания связи изделия и параметра."""
    assoc = ProductParameter(product_id=1, parameter_id=2, value="15.5")
    assert assoc.product_id == 1
    assert assoc.parameter_id == 2
    assert assoc.value == "15.5"


def test_template_instantiation():
    """Проверка создания объекта шаблона паспорта."""
    tmpl = Template(
        name="Стандартный паспорт насоса",
        file_path="pump_v1.docx",
        required_parameter_codes=["power", "weight"],
        is_active=True,
    )
    assert tmpl.name == "Стандартный паспорт насоса"
    assert tmpl.file_path == "pump_v1.docx"
    assert "power" in tmpl.required_parameter_codes
    assert tmpl.is_active is True


def test_generation_log_instantiation():
    """Проверка создания записи аудита генерации."""
    log = GenerationLog(
        product_id=1,
        template_id=1,
        status="success",
        output_filename="passport_pump_001.docx",
    )
    assert log.status == "success"
    assert log.output_filename == "passport_pump_001.docx"
    assert log.error_message is None
