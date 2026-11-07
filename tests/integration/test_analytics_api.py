"""Интеграционные тесты для аналитических эндпоинтов."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, GenerationLog, Product, Template


async def test_analytics_endpoints(client: AsyncClient, db_session: AsyncSession):
    # 1. Создаем категорию, шаблоны и изделия
    cat = Category(name="Аналитика Кат")
    db_session.add(cat)
    await db_session.flush()

    p1 = Product(sku="AN-01", name="Изделие 1", category_id=cat.id)
    p2 = Product(sku="AN-02", name="Изделие 2", category_id=cat.id)
    db_session.add_all([p1, p2])

    t1 = Template(name="Шаблон А", file_path="t1.docx", required_parameter_codes=[])
    t2 = Template(name="Шаблон Б", file_path="t2.docx", required_parameter_codes=[])
    db_session.add_all([t1, t2])
    await db_session.flush()

    # 2. Создаем записи аудита (2 успеха для p1, 1 ошибка для p2)
    logs = [
        GenerationLog(product_id=p1.id, template_id=t1.id, status="success"),
        GenerationLog(product_id=p1.id, template_id=t1.id, status="success"),
        GenerationLog(product_id=p2.id, template_id=t2.id, status="failed", error_message="Тест"),
    ]
    db_session.add_all(logs)
    await db_session.commit()

    # 3. Проверка GET /api/v1/analytics/overview
    resp_overview = await client.get("/api/v1/analytics/overview")
    assert resp_overview.status_code == 200
    ov_data = resp_overview.json()
    assert ov_data["total_generations"] == 3
    assert ov_data["success_count"] == 2
    assert ov_data["failed_count"] == 1
    assert ov_data["success_rate_percent"] == 66.7

    # 4. Проверка GET /api/v1/analytics/popular-products
    resp_popular = await client.get("/api/v1/analytics/popular-products?limit=2")
    assert resp_popular.status_code == 200
    pop_data = resp_popular.json()
    assert len(pop_data) == 1  # Только p1 имеет успешные генерации
    assert pop_data[0]["sku"] == "AN-01"
    assert pop_data[0]["generation_count"] == 2

    # 5. Проверка GET /api/v1/analytics/template-stats
    resp_tmpls = await client.get("/api/v1/analytics/template-stats")
    assert resp_tmpls.status_code == 200
    t_data = resp_tmpls.json()
    assert len(t_data) >= 2
    # Шаблон А имеет 2 успешных запуска
    t1_stat = next(item for item in t_data if item["template_name"] == "Шаблон А")
    assert t1_stat["total_runs"] == 2
    assert t1_stat["success_runs"] == 2
