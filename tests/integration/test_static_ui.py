"""Интеграционные тесты отдачи клиентского веб-интерфейса и статики."""

from httpx import AsyncClient


async def test_root_serves_html_ui(client: AsyncClient):
    """Корневой эндпоинт отдаёт HTML-страницу интерфейса генератора."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Генератор паспортов изделий" in response.text
    assert 'id="generate-form"' in response.text


async def test_static_files_availability(client: AsyncClient):
    """Статические файлы CSS и JS корректно раздаются сервером."""
    # Проверка стилей
    resp_css = await client.get("/static/style.css")
    assert resp_css.status_code == 200
    assert len(resp_css.content) > 0

    # Проверка скрипта
    resp_js = await client.get("/static/app.js")
    assert resp_js.status_code == 200
    assert "document.addEventListener" in resp_js.text
