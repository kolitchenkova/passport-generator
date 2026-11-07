"""Модульные тесты генератора типовых DOCX-шаблонов."""

import tempfile
from pathlib import Path

from docx import Document

from app.core.config import settings
from app.services.template_generator import (
    create_psu_template,
    create_spotlight_template,
    ensure_default_templates,
)


def test_create_spotlight_template():
    """Проверка генерации шаблона светодиодного/ИК прожектора."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_file = Path(tmp_dir) / "test_spotlight.docx"
        create_spotlight_template(target_file)

        assert target_file.exists()
        assert target_file.stat().st_size > 0

        doc = Document(str(target_file))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "ПАСПОРТ ИЗДЕЛИЯ" in full_text
        assert "{{ name }}" in full_text
        assert len(doc.tables) >= 1


def test_create_psu_template():
    """Проверка генерации шаблона блока питания."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_file = Path(tmp_dir) / "test_psu.docx"
        create_psu_template(target_file)

        assert target_file.exists()
        assert target_file.stat().st_size > 0

        doc = Document(str(target_file))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "ТЕХНИЧЕСКИЙ ПАСПОРТ" in full_text
        assert len(doc.tables) >= 1


def test_ensure_default_templates(monkeypatch):
    """Проверка создания шаблонов при их отсутствии и ветки повторного вызова."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_templates_dir = Path(tmp_dir)
        monkeypatch.setattr(settings, "TEMPLATES_DIR", fake_templates_dir)

        # 1. Первый вызов — создает отсутствующие файлы
        ensure_default_templates()
        assert (fake_templates_dir / "spotlight_template.docx").exists()
        assert (fake_templates_dir / "psu_template.docx").exists()

        # 2. Второй вызов — проверяет условие exists() и ничего не ломает
        ensure_default_templates()
