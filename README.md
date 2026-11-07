
# 📄 Информационная система генерации паспортов изделий по шаблонам DOCX

![CI](https://github.com/kolitchenkova/passport-generator/actions/workflows/ci.yml/badge.svg)

---

## 📌 Содержание
1. [Описание предметной области и назначения системы](#1-описание-предметной-области-и-назначения-системы)
2. [Стек технологий](#2-стек-технологий)
3. [Описание переменных окружения](#3-описание-переменных-окружения)
4. [Инструкция по запуску](#4-инструкция-по-запуску)
5. [ERD и краткое описание сущностей](#5-erd-и-краткое-описание-сущностей)
6. [Перечень бизнес-правил](#6-перечень-бизнес-правил)
7. [Описание ETL-процесса и способа его запуска](#7-описание-etl-процесса-и-способа-его-запуска)
8. [Примеры запросов к API](#8-примеры-запросов-к-api)
9. [Инструкция по запуску тестов](#9-инструкция-по-запуску-тестов)

---

## 1. Описание предметной области и назначения системы

Сервис предназначен для автоматизации работы конструкторско-технологических отделов промышленных предприятий при выпуске сопроводительной документации на продукцию.

**Номенклатура каталога:**
* Блоки вторичного электропитания (ИВЭП);
* Инфракрасные прожекторы систем видеонаблюдения;
* Светодиодные прожекторы видимого света.

**Назначение системы:**
Исключение человеческого фактора и рутинных операций при формировании паспортов изделий. Пользователь указывает артикул оборудования и шаблон, сервис извлекает нормализованные характеристики из базы данных, проверяет их полноту, выполняет подстановку значений в `.docx`-шаблон и отдает готовый файл клиенту. Каждая попытка генерации регистрируется в журнале аудита.

---

## 2. Стек технологий

* **Язык программирования:** Python 3.12.
* **Веб-фреймворк:** FastAPI (ASGI), Starlette (middleware для замера времени выполнения запросов `X-Process-Time` и логирования).
* **СУБД и ORM:** PostgreSQL 16, SQLAlchemy 2.0 (асинхронный диалект `asyncpg`, строгая типизация `Mapped` / `mapped_column`, предварительная загрузка связей через `selectinload`).
* **Миграции базы данных:** Alembic (асинхронная среда, обратимые миграции `upgrade` / `downgrade`).
* **Генерация документов:** `python-docx` (динамическая замена плейсхолдеров и автогенерация таблиц параметров).
* **Валидация и сериализация:** Pydantic v2 (`from_attributes=True`, `exclude_unset=True`, Pydantic Settings).
* **Веб-интерфейс:** Single Page Application (HTML5, Modern CSS, нативный JS Fetch API).
* **Тестирование и качество:** `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, линтер `ruff`.
* **Контейнеризация и CI/CD:** Docker (многоэтапный `Dockerfile` с запуском от non-root пользователя `app`), Docker Compose, GitHub Actions.

---

## 3. Описание переменных окружения

Конфигурация приложения считывается из файла `.env` в корне проекта через `pydantic-settings`:

| Переменная | Описание | Значение по умолчанию |
| :--- | :--- | :--- |
| `POSTGRES_USER` | Имя пользователя СУБД | `app` |
| `POSTGRES_PASSWORD` | Пароль пользователя СУБД | `app` |
| `POSTGRES_DB` | Имя рабочей базы данных | `passport_db` |
| `DATABASE_URL` | Строка подключения к рабочей БД (asyncpg) | `postgresql+asyncpg://app:app@localhost:5432/passport_db` |
| `TEST_DATABASE_URL` | Строка подключения к тестовой БД | `postgresql+asyncpg://app:app@localhost:5432/passport_test` |

Для быстрого старта шаблон переменных находится в файле `.env.example`:

```bash
cp .env.example .env
```

---

## 4. Инструкция по запуску

### Вариант 1. Локальный запуск (для разработки)

1. Клонируйте репозиторий:
```bash
git clone https://github.com/lotov/passport-generator.git
cd passport-generator
```

2. Подготовьте локальный файл переменных окружения:
```bash
cp .env.example .env
```

3. Создайте и активируйте виртуальное окружение Python 3.12:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

4. Запустите СУБД PostgreSQL в Docker:
```powershell
docker compose up -d db
```

5. Примените миграции Alembic и наполните базу первичными данными:
```powershell
alembic upgrade head
python -m app.etl.seed
```

6. Запустите сервер разработки:
```powershell
uvicorn app.main:app --reload
```

7. Доступ к приложению:
* **Веб-интерфейс:** `http://127.0.0.1:8000/`
* **Swagger UI:** `http://127.0.0.1:8000/docs`

---

### Вариант 2. Запуск через Docker Compose

Весь стек разворачивается автоматически:

1. Подготовьте файл переменных окружения:
```bash
cp .env.example .env
```

2. Соберите образы и запустите контейнеры:
```bash
docker compose up --build -d
```

3. Наполните базу данных через контейнер:
```bash
docker compose exec app python -m app.etl.seed
```

4. Доступ к сервисам:
* **Веб-интерфейс:** `http://localhost:8000/`
* **Swagger UI:** `http://localhost:8000/docs`

5. Остановка сервисов:
```bash
docker compose down
```

---

## 5. ERD и краткое описание сущностей

### Диаграмма связей сущностей (Mermaid)

```mermaid
erDiagram
    CATEGORIES ||--o{ PRODUCTS : contains
    PRODUCTS ||--o{ PRODUCT_PARAMETERS : has
    PARAMETERS ||--o{ PRODUCT_PARAMETERS : used_in
    PRODUCTS ||--o{ GENERATION_LOG : generated_for
    TEMPLATES ||--o{ GENERATION_LOG : used_template

    CATEGORIES {
        int id PK
        string name UK "UNIQUE, NOT NULL"
    }

    PRODUCTS {
        int id PK
        string sku UK "UNIQUE, NOT NULL, CHECK length >= 3"
        string name "NOT NULL"
        int category_id FK "NOT NULL, ON DELETE RESTRICT"
        datetime created_at "NOT NULL, server_default now()"
    }

    PARAMETERS {
        int id PK
        string code UK "UNIQUE, NOT NULL"
        string title "NOT NULL"
        string unit "NULLable"
    }

    PRODUCT_PARAMETERS {
        int product_id PK,FK "ON DELETE CASCADE"
        int parameter_id PK,FK "ON DELETE RESTRICT"
        string value "NOT NULL"
    }

    TEMPLATES {
        int id PK
        string name "NOT NULL"
        string file_path UK "UNIQUE, NOT NULL"
        json required_parameter_codes "JSONB, NOT NULL"
        bool is_active "NOT NULL, DEFAULT true"
    }

    GENERATION_LOG {
        int id PK
        int product_id FK "NOT NULL, ON DELETE RESTRICT"
        int template_id FK "NOT NULL, ON DELETE RESTRICT"
        datetime created_at "NOT NULL, server_default now()"
        string status "NOT NULL, CHECK (status IN ('success','failed'))"
        string output_filename "NULLable"
        string error_message "NULLable, Text"
    }
```

### Краткое описание сущностей:
* **`categories`** — категории оборудования (Блоки питания, ИК-прожекторы, Прожекторы видимого света).
* **`products`** — каталог изделий с уникальным заводским артикулом (SKU) и ограничением длины `CHECK(length(sku) >= 3)`.
* **`parameters`** — нормализованный справочник технико-эксплуатационных характеристик (код, наименование, единица измерения).
* **`product_parameters`** — ассоциативная таблица связи $M:M$, определяющая значения характеристик для каждого конкретного изделия.
* **`templates`** — справочник зарегистрированных DOCX-шаблонов со списком обязательных кодов параметров (`required_parameter_codes`).
* **`generation_log`** — журнал аудита истории генераций паспортов со статусами `success`/`failed`, именем файла и текстом ошибки (FK защищены через `ON DELETE RESTRICT`).

---

## 6. Перечень бизнес-правил

Вся бизнес-логика вынесена в сервисный слой (`app/services/passport_service.py`):

1. **Правило 1. Валидация полноты данных изделия перед генерацией:**  
   Перед формированием документа сервис проверяет, чтобы изделие содержало все обязательные параметры, требуемые выбранным шаблоном (`required_parameter_codes`). Если хотя бы один параметр не заполнен, генерация блокируется, в `generation_log` фиксируется запись со статусом `failed`, а API возвращает **HTTP 422 Unprocessable Content** с детальным списком недостающих кодов.
2. **Правило 2. Идемпотентность и дедупликация генераций:**  
   Если для комбинации изделия и шаблона `(product_id, template_id)` за последние **10 минут** уже был успешно сформирован паспорт, система не создает повторный файл на диске, а возвращает существующий документ с метаданными и признаком **`reused: true`**.
3. **Правило 3. Транзакционный аудит и устойчивость к сбоям:**  
   Процесс формирования паспорта атомарен. Любая попытка генерации фиксируется в базе данных. В случае системного сбоя (поврежден шаблон, ошибка диска) операция аудита не откатывается, а сохраняет в БД статус `failed` и текст возникшего исключения для расследования инцидента.
4. **Правило 4. Аналитическая агрегация истории:**  
   Эндпоинты аналитики выполняют расчет показателей (процент успешных генераций, топ популярных изделий, надежность шаблонов) средствами SQL-агрегатов (`GROUP BY`, `COUNT`, `FILTER`) непосредственно в СУБД.

---

## 7. Описание ETL-процесса и способа его запуска

Для пакетной загрузки новых изделий от смежных отделов реализован CLI-скрипт **`app/etl/import_data.py`**.

### Этапы конвейера:
1. **Extract:** Потоковое чтение CSV-файла с автоопределением кодировки UTF-8 с BOM (`utf-8-sig`).
2. **Transform (Очистка и валидация):**
   * Удаление краевых пробелов строк;
   * Проверка обязательных полей (`sku`, `name`, `category`);
   * Валидация длины артикула ($\ge 3$ символов);
   * Отсев дублирующихся артикулов внутри самого файла.
3. **Load (Загрузка в БД):**
   * **Идемпотентность:** изделия, уже присутствующие в базе данных, пропускаются;
   * **Автосоздание категорий:** если категория из CSV отсутствует в базе, она создается автоматически;
   * Привязка значений характеристик к справочнику `parameters`.
4. **Аудит:** Логирование хода импорта и вывод финальной сводки (прочитано, добавлено, пропущено по типам ошибок).

### Команда запуска:
```bash
python -m app.etl.import_data --source data/csv/products.csv
```

---

## 8. Примеры запросов к API

### 1. Успешный запрос информации об изделиях в категории

<img width="1414" height="810" alt="{3AF1101D-E294-4C4F-B89F-B00A79B5BA5C}" src="https://github.com/user-attachments/assets/a7080d5e-6fd7-4b5a-92b1-683d496514ca" />
<img width="1417" height="859" alt="{5FB09DA7-942D-4F9B-A959-9A169C34C91A}" src="https://github.com/user-attachments/assets/a3b542c8-8c0b-49f6-b878-1a146bee8231" />

### 2. Генерация паспорта изделия

<img width="1420" height="779" alt="{1D22A83B-C4DF-442B-80A3-0AE808F830D5}" src="https://github.com/user-attachments/assets/eb4b15b1-3b19-4a3f-936e-61cb75cb54e3" />
<img width="1413" height="673" alt="{F545E2E6-8DB3-4036-BEE7-E397E46651BE}" src="https://github.com/user-attachments/assets/2ce7b433-f5d2-4e65-82f9-8bba1b721ff7" />
<img width="1170" height="716" alt="{7AA2BB02-7071-41B9-BCF1-4FD5111CD797}" src="https://github.com/user-attachments/assets/73841b1a-0702-4662-b37a-c52f4fefa77a" />


### 3. Ошибка нехватки обязательных параметров

<img width="568" height="386" alt="{45F44859-6EED-41CA-B7C6-3DCF1C84B95E}" src="https://github.com/user-attachments/assets/c252a921-2dd3-4f26-898c-bc56a0478b27" />
<img width="754" height="591" alt="{8990CCFD-8213-48C3-9E3C-B605607E5686}" src="https://github.com/user-attachments/assets/b97c050c-9afd-49da-a678-ac32f6cd8520" />
<img width="1183" height="788" alt="{A2932199-F7BA-4118-B6D2-49B5E25E4C95}" src="https://github.com/user-attachments/assets/8bef4ff3-364e-467b-80d1-16f8df0c23dd" />

### 4. Сводная аналитика генераций
<img width="864" height="450" alt="{FE39B6D1-D66E-4C58-8B48-4AC0832117A8}" src="https://github.com/user-attachments/assets/5ce2c3df-191e-48bf-b78f-d92db08d560d" />
<img width="914" height="767" alt="{D8252CE4-39E4-4FFB-9AA0-A0BE4607988E}" src="https://github.com/user-attachments/assets/b52a20b2-0d32-40c4-bb2b-5f5ac5f4ee47" />

---

## 9. Инструкция по запуску тестов

Тестовый набор включает модульные и сквозные интеграционные тесты для API, бизнес-правил, генератора документов и ETL-очистки. Тесты используют изолированную базу данных `passport_test`.

### Локальный запуск тестов:
```bash
pytest -v
```

### Запуск тестов в контейнере Docker:
```bash
docker compose run --rm tests
```

### Проверка стиля и форматирования линтером:
```bash
ruff check .
ruff format --check .
```
