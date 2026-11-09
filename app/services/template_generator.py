"""Генератор стандартных DOCX-шаблонов паспортов изделий."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from app.core.config import settings


def create_spotlight_template(target_path: Path) -> None:
    """Создать типовой шаблон паспорта светодиодного/ИК прожектора."""
    doc = Document()

    # Поля страницы
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

    # Заголовок документа
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.add_run("ПАСПОРТ ИЗДЕЛИЯ")
    run_title.bold = True
    run_title.font.size = Pt(18)
    run_title.font.color.rgb = RGBColor(0x1F, 0x4E, 0x78)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = sub.add_run("Осветительное и прожекторное оборудование")
    run_sub.font.size = Pt(12)
    run_sub.italic = True

    doc.add_paragraph()  # отступ

    # Раздел 1. Общие сведения
    h1 = doc.add_heading("1. Общие сведения об изделии", level=1)
    h1.paragraph_format.space_before = Pt(10)

    doc.add_paragraph("Наименование изделия: {{ name }}")
    doc.add_paragraph("Заводской артикул (SKU): {{ sku }}")
    doc.add_paragraph("Категория: {{ category_name }}")
    doc.add_paragraph("Дата оформления паспорта: {{ date }}")

    # Раздел 2. Технические характеристики
    h2 = doc.add_heading("2. Основные технические параметры", level=1)
    h2.paragraph_format.space_before = Pt(14)

    # Таблица технических характеристик
    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    headers = ["№ п/п", "Параметр", "Значение", "Ед. изм."]
    hdr_cells = table.rows[0].cells
    for i, title_text in enumerate(headers):
        hdr_cells[i].text = title_text
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True

    # Заглушка строки для динамического заполнения параметров
    row_cells = table.add_row().cells
    row_cells[0].text = "1"
    row_cells[1].text = "Напряжение питания (voltage)"
    row_cells[2].text = "{{ voltage }}"
    row_cells[3].text = "В"

    row_cells2 = table.add_row().cells
    row_cells2[0].text = "2"
    row_cells2[1].text = "Потребляемая мощность (power)"
    row_cells2[2].text = "{{ power }}"
    row_cells2[3].text = "Вт"

    row_cells3 = table.add_row().cells
    row_cells3[0].text = "3"
    row_cells3[1].text = "Номинальный ток (current)"
    row_cells3[2].text = "{{ current }}"
    row_cells3[3].text = "А"

    row_cells4 = table.add_row().cells
    row_cells4[0].text = "4"
    row_cells4[1].text = "Световой поток (luminous_flux)"
    row_cells4[2].text = "{{ luminous_flux }}"
    row_cells4[3].text = "лм"

    # Раздел 3. Гарантии
    h3 = doc.add_heading("3. Гарантийные обязательства", level=1)
    h3.paragraph_format.space_before = Pt(14)
    doc.add_paragraph(
        "Предприятие-изготовитель гарантирует соответствие изделия техническим условиям "
        "при соблюдении потребителем правил транспортирования, хранения и монтажа. "
        "Срок гарантии: 24 месяца со дня ввода в эксплуатацию."
    )

    doc.save(str(target_path))


def create_psu_template(target_path: Path) -> None:
    """Создать типовой шаблон паспорта блока питания (ИВЭП)."""
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.add_run("ТЕХНИЧЕСКИЙ ПАСПОРТ")
    run_title.bold = True
    run_title.font.size = Pt(18)
    run_title.font.color.rgb = RGBColor(0x2E, 0x5B, 0x82)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = sub.add_run("Источники вторичного электропитания стабилизированные")
    run_sub.font.size = Pt(12)
    run_sub.italic = True

    doc.add_heading("1. Сведения об изделии", level=1)
    doc.add_paragraph("Модель: {{ name }}")
    doc.add_paragraph("Артикул: {{ sku }}")
    doc.add_paragraph("Категория оборудования: {{ category_name }}")
    doc.add_paragraph("Дата выпуска: {{ date }}")

    doc.add_heading("2. Электрические характеристики", level=1)
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Параметр", "Значение", "Ед. изм."]
    hdr_cells = table.rows[0].cells
    for i, title_text in enumerate(headers):
        hdr_cells[i].text = title_text
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True

    r1 = table.add_row().cells
    r1[0].text = "Выходное напряжение (voltage)"
    r1[1].text = "{{ voltage }}"
    r1[2].text = "В"

    r2 = table.add_row().cells
    r2[0].text = "Выходной ток (current)"
    r2[1].text = "{{ current }}"
    r2[2].text = "А"

    r3 = table.add_row().cells
    r3[0].text = "Выходная мощность (power)"
    r3[1].text = "{{ power }}"
    r3[2].text = "Вт"

    doc.add_heading("3. Свидетельство о приемке", level=1)
    doc.add_paragraph(
        "Изделие признано годным для эксплуатации. Отдел технического контроля (ОТК): Штамп годен."
    )

    doc.save(str(target_path))


def ensure_default_templates() -> None:
    """Гарантировать наличие типовых DOCX-файлов шаблонов на диске."""
    settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    settings.GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    spotlight_file = settings.TEMPLATES_DIR / "spotlight_template.docx"
    if not spotlight_file.exists():
        create_spotlight_template(spotlight_file)

    psu_file = settings.TEMPLATES_DIR / "psu_template.docx"
    if not psu_file.exists():
        create_psu_template(psu_file)
