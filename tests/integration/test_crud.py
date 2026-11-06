from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationLog, Template


# 1. Создание категории и изделия со связями M:M (201 Created)
async def test_create_category_and_product_with_params(client: AsyncClient):
    cat_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Инфракрасные прожекторы"},
    )
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    param_resp = await client.post(
        "/api/v1/parameters",
        json={"code": "power_w", "title": "Мощность", "unit": "Вт"},
    )
    assert param_resp.status_code == 201
    param_id = param_resp.json()["id"]

    # Создание изделия с характеристиками M:M
    prod_payload = {
        "sku": "IR-850-050",
        "name": "Прожектор ИК-850",
        "category_id": cat_id,
        "parameters": [{"parameter_id": param_id, "value": "50"}],
    }
    prod_resp = await client.post("/api/v1/products", json=prod_payload)
    assert prod_resp.status_code == 201
    prod_data = prod_resp.json()
    assert prod_data["sku"] == "IR-850-050"
    assert "id" in prod_data


# 2.Негативные проверки создания изделия: дубликат SKU (409), короткий SKU(422), нет категории(404)
async def test_create_product_negative_cases(client: AsyncClient):
    cat_id = (await client.post("/api/v1/categories", json={"name": "БП"})).json()["id"]

    payload = {"sku": "PSU-12-050", "name": "БП 12В", "category_id": cat_id}
    res1 = await client.post("/api/v1/products", json=payload)
    assert res1.status_code == 201

    # Дубликат SKU (409)
    res_dup = await client.post("/api/v1/products", json=payload)
    assert res_dup.status_code == 409
    assert "уже существует" in res_dup.json()["detail"]

    # Слишком короткий SKU (422)
    res_short = await client.post(
        "/api/v1/products",
        json={"sku": "AA", "name": "Короткий", "category_id": cat_id},
    )
    assert res_short.status_code == 422

    # Несуществующая категория (404)
    res_no_cat = await client.post(
        "/api/v1/products",
        json={"sku": "VALID-SKU", "name": "Без категории", "category_id": 99999},
    )
    assert res_no_cat.status_code == 404


# 3. Фильтрация, поиск, пагинация и сортировка изделий
async def test_products_filter_pagination_and_sorting(client: AsyncClient):
    c1 = (await client.post("/api/v1/categories", json={"name": "Свет 1"})).json()["id"]
    c2 = (await client.post("/api/v1/categories", json={"name": "Свет 2"})).json()["id"]

    await client.post(
        "/api/v1/products",
        json={"sku": "P-101", "name": "Прожектор Альфа", "category_id": c1},
    )
    await client.post(
        "/api/v1/products",
        json={"sku": "P-102", "name": "Прожектор Бета", "category_id": c1},
    )
    await client.post(
        "/api/v1/products",
        json={"sku": "P-201", "name": "Фонарь Гамма", "category_id": c2},
    )

    # Фильтр по категории
    res_cat = await client.get(f"/api/v1/products?category_id={c1}")
    assert res_cat.status_code == 200
    assert len(res_cat.json()) == 2

    # Поиск по имени и сортировка desc
    res_search = await client.get("/api/v1/products?search=Прожектор&sort_order=desc")
    assert res_search.status_code == 200
    assert len(res_search.json()) == 2

    # Пагинация
    res_p1 = await client.get(f"/api/v1/products?category_id={c1}&limit=1&offset=0")
    res_p2 = await client.get(f"/api/v1/products?category_id={c1}&limit=1&offset=1")
    assert len(res_p1.json()) == 1 and len(res_p2.json()) == 1
    assert res_p1.json()[0]["id"] != res_p2.json()[0]["id"]


# 4. Детальное получение изделия со связями M:M и 404
async def test_get_product_detail(client: AsyncClient):
    c_id = (await client.post("/api/v1/categories", json={"name": "Оптика"})).json()["id"]
    p_id = (
        await client.post(
            "/api/v1/parameters",
            json={"code": "angle", "title": "Угол", "unit": "град"},
        )
    ).json()["id"]

    prod_id = (
        await client.post(
            "/api/v1/products",
            json={
                "sku": "LENS-01",
                "name": "Линза",
                "category_id": c_id,
                "parameters": [{"parameter_id": p_id, "value": "30"}],
            },
        )
    ).json()["id"]

    # Успешное получение со связями
    res = await client.get(f"/api/v1/products/{prod_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["category_name"] == "Оптика"
    assert len(data["parameters"]) == 1
    assert data["parameters"][0]["parameter_code"] == "angle"

    # 404 при получении несуществующего изделия
    res_404 = await client.get("/api/v1/products/99999")
    assert res_404.status_code == 404


# 5. Все сценарии обновления PATCH (успех, 404 изделия, 404 категории, 409 дубликат SKU)
async def test_patch_product_all_scenarios(client: AsyncClient):
    c1 = (await client.post("/api/v1/categories", json={"name": "Кат А"})).json()["id"]
    c2 = (await client.post("/api/v1/categories", json={"name": "Кат Б"})).json()["id"]

    p1 = (
        await client.post(
            "/api/v1/products",
            json={"sku": "SKU-001", "name": "Имя 1", "category_id": c1},
        )
    ).json()
    p2 = (
        await client.post(
            "/api/v1/products",
            json={"sku": "SKU-002", "name": "Имя 2", "category_id": c1},
        )
    ).json()

    # Успешный PATCH (меняем категорию и имя)
    res_ok = await client.patch(
        f"/api/v1/products/{p1['id']}",
        json={"name": "Новое имя", "category_id": c2},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["name"] == "Новое имя"
    assert res_ok.json()["category_id"] == c2

    # Ошибка 404: изделия нет
    res_no_prod = await client.patch("/api/v1/products/99999", json={"name": "Тест"})
    assert res_no_prod.status_code == 404

    # Ошибка 404: категории нет
    res_no_cat = await client.patch(
        f"/api/v1/products/{p1['id']}",
        json={"category_id": 99999},
    )
    assert res_no_cat.status_code == 404

    # Ошибка 409: попытка занять SKU второго изделия
    res_dup_sku = await client.patch(
        f"/api/v1/products/{p1['id']}",
        json={"sku": p2["sku"]},
    )
    assert res_dup_sku.status_code == 409


# 6. Все сценарии удаления DELETE (успех 204, 404 нет изделия, 409 есть история)
async def test_delete_product_all_scenarios(client: AsyncClient, db_session: AsyncSession):
    cat_id = (await client.post("/api/v1/categories", json={"name": "Удаляемые"})).json()["id"]
    prod = (
        await client.post(
            "/api/v1/products",
            json={"sku": "DEL-100", "name": "На удаление", "category_id": cat_id},
        )
    ).json()

    # 1. Создаем шаблон и запись аудита через фикстуру db_session
    tmpl = Template(name="Шаблон", file_path="del_tmpl.docx")
    db_session.add(tmpl)
    await db_session.flush()

    log = GenerationLog(product_id=prod["id"], template_id=tmpl.id, status="success")
    db_session.add(log)
    await db_session.commit()

    # 2. Попытка удалить изделие с историей -> 409 Conflict (защита внешнего ключа)
    res_conflict = await client.delete(f"/api/v1/products/{prod['id']}")
    assert res_conflict.status_code == 409
    assert "история" in res_conflict.json()["detail"]

    # 3. Удаляем блокирующий лог и пробуем снова
    await db_session.delete(log)
    await db_session.commit()

    # 4. Успешное удаление -> 204
    res_del = await client.delete(f"/api/v1/products/{prod['id']}")
    assert res_del.status_code == 204

    # 5. Повторный запрос -> 404
    res_404 = await client.get(f"/api/v1/products/{prod['id']}")
    assert res_404.status_code == 404

    # 6. Удаление несуществующего -> 404
    res_del_404 = await client.delete("/api/v1/products/99999")
    assert res_del_404.status_code == 404


# 7. Проверка заголовка X-Process-Time
async def test_process_time_header_present(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "x-process-time" in resp.headers
    assert resp.headers["x-process-time"].endswith("ms")
