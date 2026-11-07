"""Сервисный слой генерации паспортов изделий с реализацией бизнес-правил."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from docx import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import GenerationLog, Product, ProductParameter, Template
from app.services.exceptions import (
    IncompleteParametersError,
    PassportRenderError,
    ProductNotFoundError,
    TemplateNotFoundError,
)
from app.services.template_generator import ensure_default_templates


class PassportService:
    """Сервис для валидации данных, дедупликации и генерации паспортов DOCX."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_passport(
        self,
        product_id: int,
        template_id: int,
        deduplication_minutes: int = 10,
    ) -> tuple[GenerationLog, bool]:
        """Основной метод генерации паспорта.

        Возвращает кортеж: (запись_GenerationLog, флаг_reused).
        """
        # Гарантируем, что стандартные файлы шаблонов существуют на диске
        ensure_default_templates()

        # 1. Загрузка изделия со связями M:M и категории
        query_prod = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.parameters_assoc).selectinload(ProductParameter.parameter),
            )
        )
        product = (await self.session.scalars(query_prod)).first()
        if not product:
            raise ProductNotFoundError(f"Изделие с ID {product_id} не найдено")

        # 2. Загрузка шаблона
        template = await self.session.get(Template, template_id)
        if not template or not template.is_active:
            raise TemplateNotFoundError(f"Активный шаблон с ID {template_id} не найден")

        # -----------------------------------------------------------------
        # БИЗНЕС-ПРАВИЛО 2: Идемпотентность и дедупликация генераций
        # -----------------------------------------------------------------
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=deduplication_minutes)
        dedup_query = (
            select(GenerationLog)
            .where(
                GenerationLog.product_id == product_id,
                GenerationLog.template_id == template_id,
                GenerationLog.status == "success",
                GenerationLog.created_at >= cutoff_time,
            )
            .order_by(GenerationLog.created_at.desc())
            .limit(1)
        )
        cached_log = (await self.session.scalars(dedup_query)).first()

        if cached_log and cached_log.output_filename:
            existing_file = settings.GENERATED_DIR / cached_log.output_filename
            if existing_file.exists():
                # Возвращаем существующую запись с флагом reused=True без создания дубликата файла
                return cached_log, True

        # -----------------------------------------------------------------
        # БИЗНЕС-ПРАВИЛО 1: Проверка полноты данных перед генерацией
        # -----------------------------------------------------------------
        # Собираем словарь существующих параметров изделия: code -> value
        available_params: dict[str, str] = {
            assoc.parameter.code: assoc.value
            for assoc in product.parameters_assoc
            if assoc.parameter and assoc.parameter.code
        }

        required_codes: list[str] = template.required_parameter_codes or []
        missing_codes = [code for code in required_codes if code not in available_params]

        if missing_codes:
            # БИЗНЕС-ПРАВИЛО 3 (аудит сбоя): фиксируем неудачную попытку в логе
            failed_log = GenerationLog(
                product_id=product_id,
                template_id=template_id,
                status="failed",
                error_message=f"Отсутствуют обязательные параметры: {', '.join(missing_codes)}",
            )
            self.session.add(failed_log)
            await self.session.commit()
            raise IncompleteParametersError(missing_parameters=missing_codes)

        # -----------------------------------------------------------------
        # БИЗНЕС-ПРАВИЛО 3: Транзакционная генерация и DOCX-рендеринг
        # -----------------------------------------------------------------
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_sku = re.sub(r"[^\w\-]", "_", product.sku)
        output_filename = f"passport_{safe_sku}_{timestamp_str}.docx"
        output_path = settings.GENERATED_DIR / output_filename

        # Формируем контекст подстановки
        context: dict[str, str] = {
            "name": product.name,
            "sku": product.sku,
            "category_name": product.category.name if product.category else "—",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        context.update(available_params)

        try:
            self._render_docx(
                template_path=Path(template.file_path),
                output_path=output_path,
                context=context,
            )
        except Exception as exc:
            # Фиксация системной ошибки рендеринга в аудите
            failed_log = GenerationLog(
                product_id=product_id,
                template_id=template_id,
                status="failed",
                error_message=f"Ошибка рендеринга: {str(exc)}",
            )
            self.session.add(failed_log)
            await self.session.commit()
            raise PassportRenderError(f"Не удалось сгенерировать DOCX: {str(exc)}") from exc

        # Успешная генерация: коммитим запись аудита в БД
        success_log = GenerationLog(
            product_id=product_id,
            template_id=template_id,
            status="success",
            output_filename=output_filename,
            error_message=None,
        )
        self.session.add(success_log)
        await self.session.commit()
        await self.session.refresh(success_log)

        return success_log, False

    def _render_docx(
        self,
        template_path: Path,
        output_path: Path,
        context: dict[str, str],
    ) -> None:
        """Подстановка значений из context в плейсхолдеры шаблона DOCX."""
        if not template_path.exists():
            raise FileNotFoundError(f"Файл шаблона не найден: {template_path}")

        doc = Document(str(template_path))

        # Замена плейсхолдеров в обычных абзацах
        for p in doc.paragraphs:
            self._replace_placeholders_in_paragraph(p, context)

        # Замена плейсхолдеров в ячейках таблиц
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        self._replace_placeholders_in_paragraph(p, context)

        doc.save(str(output_path))

    @staticmethod
    def _replace_placeholders_in_paragraph(paragraph, context: dict[str, str]) -> None:
        """Безопасная замена {{ key }} и {{key}} в тексте абзаца."""
        for key, val in context.items():
            pattern_spaced = f"{{{{ {key} }}}}"
            pattern_clean = f"{{{{{key}}}}}"
            if pattern_spaced in paragraph.text:
                paragraph.text = paragraph.text.replace(pattern_spaced, str(val))
            if pattern_clean in paragraph.text:
                paragraph.text = paragraph.text.replace(pattern_clean, str(val))
