"""Интеграционные тесты API генерации и скачивания паспортов."""

from httpx import AsyncClient


async def test_passport_generation_and_download_flow(client: AsyncClient):
    # 1. Создаем категорию
    cat_id = (await client.post("/api/v1/categories", json={"name": "Кат Свет"})).json()["id"]

    # 2. Создаем параметр
    p_id = (
        await client.post(
            "/api/v1/parameters",
            json={"code": "power", "title": "Мощность", "unit": "Вт"},
        )
    ).json()["id"]

    # 3. Регистрируем шаблон, требующий 'power'
    tmpl_id = (
        await client.post(
            "/api/v1/templates",
            json={
                "name": "Шаблон мини",
                "file_path": "data/templates/psu_template.docx",
                "required_parameter_codes": ["power"],
            },
        )
    ).json()["id"]

    # 4. Создаем изделие со значением 'power'
    prod_id = (
        await client.post(
            "/api/v1/products",
            json={
                "sku": "SKU-FLOW-01",
                "name": "Фонарь",
                "category_id": cat_id,
                "parameters": [{"parameter_id": p_id, "value": "10"}],
            },
        )
    ).json()["id"]

    # 5. Вызываем генерацию (POST /api/v1/passports/generate)
    gen_resp = await client.post(
        "/api/v1/passports/generate",
        json={"product_id": prod_id, "template_id": tmpl_id},
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["status"] == "success"
    assert gen_data["reused"] is False
    assert "download_url" in gen_data
    log_id = gen_data["log_id"]

    # 6. Проверяем дедупликацию (повторный запрос)
    gen_repeat = await client.post(
        "/api/v1/passports/generate",
        json={"product_id": prod_id, "template_id": tmpl_id},
    )
    assert gen_repeat.status_code == 200
    assert gen_repeat.json()["reused"] is True

    # 7. Скачиваем сформированный файл (GET /api/v1/passports/{log_id}/download)
    dl_resp = await client.get(f"/api/v1/passports/{log_id}/download")
    assert dl_resp.status_code == 200
    assert (
        dl_resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(dl_resp.content) > 0

    # 8. Проверка негативного кейса: шаблон требует параметр, которого нет -> 422
    tmpl_strict_id = (
        await client.post(
            "/api/v1/templates",
            json={
                "name": "Строгий шаблон",
                "file_path": "data/templates/spotlight_template.docx",
                "required_parameter_codes": ["power", "absent_parameter"],
            },
        )
    ).json()["id"]

    gen_fail = await client.post(
        "/api/v1/passports/generate",
        json={"product_id": prod_id, "template_id": tmpl_strict_id},
    )
    assert gen_fail.status_code == 422
    assert "absent_parameter" in gen_fail.json()["detail"]["missing_parameters"]
