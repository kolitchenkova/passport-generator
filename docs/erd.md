# 🗄 ER-диаграмма базы данных (Entity-Relationship Diagram)

Данная схема описывает структуру реляционной базы данных сервиса генерации паспортов изделий на PostgreSQL.

---

## Графическая диаграмма связей (Mermaid)

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

---

## Описание сущностей и типов связей

1. **`categories` $\rightarrow$ `products` (Один-ко-многим / 1:M)**  
   Каждое изделие строго принадлежит одной категории (Блоки питания, ИК-прожекторы, Прожекторы видимого света).
2. **`products` $\leftrightarrow$ `parameters` через `product_parameters` (Многие-ко-многим / M:M)**  
   Ассоциативная таблица со связкой `(product_id, parameter_id)` и текстовым полем `value`. Позволяет задавать произвольный состав технических характеристик без денормализации.
3. **`products` $\rightarrow$ `generation_log` (1:M) и `templates` $\rightarrow$ `generation_log` (1:M)**  
   Журнал аудита генераций. Каждая запись связывает изделие, использованный шаблон, статус операции (`success`/`failed`), имя сформированного файла и возможную ошибку.

---

## Ограничения целостности и индексы
* **Ограничения CHECK:**
  * `check_product_sku_min_length`: `length(sku) >= 3`
  * `check_generation_log_status`: `status IN ('success', 'failed')`
* **Ограничения внешних ключей (FK):**  
  Все внешние ключи, связывающие историю генераций с изделиями и шаблонами, имеют режим **`ON DELETE RESTRICT`**, защищая историю аудита от случайного удаления изделий.
* **Индексы для производительности:**
  * `idx_products_sku` — быстрый поиск изделий по заводскому артикулу;
  * `idx_products_category` — быстрая фильтрация по категории;
  * `idx_generation_log_created` — выборка для правила дедупликации (окно 10 минут) и построения аналитических отчетов;
  * `idx_product_parameters_product` — быстрая сборка характеристик изделия при рендеринге документа.
