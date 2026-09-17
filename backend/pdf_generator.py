import io
import os
from typing import Any, Dict
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


FONT_REGULAR = "Arial"
FONT_BOLD = "Arial-Bold"

def init_pdf_fonts():
    # Priority 1: Bundled font in project (guaranteed to work on Vercel/Linux/Docker)
    bundled_dir = os.path.join(os.path.dirname(__file__), "fonts")
    b_reg = os.path.join(bundled_dir, "CustomArial.ttf")
    b_bold = os.path.join(bundled_dir, "CustomArial-Bold.ttf")
    if os.path.exists(b_reg) and os.path.exists(b_bold):
        try:
            if "CustomArial" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("CustomArial", b_reg))
                pdfmetrics.registerFont(TTFont("CustomArial-Bold", b_bold))
            return "CustomArial", "CustomArial-Bold"
        except Exception:
            pass

    # Priority 2: Windows system fonts
    win_arial = "C:/Windows/Fonts/arial.ttf"
    win_arial_bd = "C:/Windows/Fonts/arialbd.ttf"
    if os.path.exists(win_arial) and os.path.exists(win_arial_bd):
        try:
            if "CustomArial" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("CustomArial", win_arial))
                pdfmetrics.registerFont(TTFont("CustomArial-Bold", win_arial_bd))
            return "CustomArial", "CustomArial-Bold"
        except Exception:
            pass

    return "Helvetica", "Helvetica-Bold"


class NumberedCanvas(canvas.Canvas):
    """Adds clean running footer and page numbers without emoji artifacts."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        font_name = "CustomArial" if "CustomArial" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#64748b"))
        footer_text = f"Материал канала @yanv_tg | Экспресс-аудит: @yanvtg | Страница {self._pageNumber} из {page_count}"
        self.drawRightString(A4[0] - 16 * mm, 9 * mm, footer_text)
        self.restoreState()


def generate_audit_pdf(audit_data: Dict[str, Any]) -> bytes:
    """Builds a pixel-perfect, branded PDF report matching Yan's original layout."""
    f_reg, f_bold = init_pdf_fonts()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm
    )

    # Styles
    style_logo_text = ParagraphStyle(
        "LogoText",
        fontName=f_bold,
        fontSize=13,
        leading=13,
        textColor=colors.white,
        alignment=1
    )
    style_author_name = ParagraphStyle(
        "AuthorName",
        fontName=f_bold,
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2
    )
    style_author_links = ParagraphStyle(
        "AuthorLinks",
        fontName=f_reg,
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#2563eb")
    )
    style_badge_year = ParagraphStyle(
        "BadgeYear",
        fontName=f_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
        alignment=1
    )
    style_kicker = ParagraphStyle(
        "Kicker",
        fontName=f_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#dc2626"),
        spaceBefore=10,
        spaceAfter=3
    )
    style_doc_title = ParagraphStyle(
        "DocTitle",
        fontName=f_bold,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )
    style_meta_row = ParagraphStyle(
        "MetaRow",
        fontName=f_reg,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=6
    )
    style_doc_desc = ParagraphStyle(
        "DocDesc",
        fontName=f_reg,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8
    )
    style_block_title = ParagraphStyle(
        "BlockTitle",
        fontName=f_bold,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0f172a")
    )
    style_fine_tag = ParagraphStyle(
        "FineTag",
        fontName=f_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#dc2626"),
        alignment=2
    )
    style_item_title = ParagraphStyle(
        "ItemTitle",
        fontName=f_bold,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )

    story = []

    # 1. Header with authentic D/ Logo box, Name and Year Pill
    # D/ Logo block: black rounded square
    logo_table = Table([[Paragraph("D/", style_logo_text)]], colWidths=[8.5 * mm], rowHeights=[8.5 * mm])
    logo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#000000")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))

    # Author text block
    author_info = [
        [Paragraph("Ян", style_author_name)],
        [Paragraph("<a href='https://t.me/yanv_tg' color='#2563eb'><u>@yanv_tg</u></a> &nbsp;<font color='#64748b'>(связь <a href='https://t.me/yanvtg' color='#2563eb'><u>@yanvtg</u></a>)</font>", style_author_links)]
    ]
    author_table = Table(author_info, colWidths=[100 * mm])
    author_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))

    # Year Pill Badge
    badge_table = Table([[Paragraph("АКТУАЛЬНО НА 2026 ГОД", style_badge_year)]], colWidths=[52 * mm])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))

    # Assemble main header
    header_data = [[
        Table([[logo_table, author_table]], colWidths=[12 * mm, 105 * mm]),
        badge_table
    ]]
    header_table = Table(header_data, colWidths=[122 * mm, 56 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # 2. Document Title & Site Meta
    story.append(Paragraph("ЧЕК-ЛИСТ АУДИТА И ЮРИДИЧЕСКОЙ ЗАЩИТЫ", style_kicker))
    story.append(Paragraph("Требования к сайтам в РФ на 2026 год", style_doc_title))

    domain = audit_data.get("domain", "Сайт")
    platform = audit_data.get("cms_platform", "Сайт / HTML")
    site_type = audit_data.get("site_type", "Сайт услуг")
    hosting = audit_data.get("hosting_provider", "Хостинг")

    story.append(Paragraph(
        f"<b>Домен:</b> {domain} &nbsp;|&nbsp; <b>Тип:</b> {site_type} &nbsp;|&nbsp; <b>Движок:</b> {platform} &nbsp;|&nbsp; <b>Хостинг:</b> {hosting}",
        style_meta_row
    ))

    story.append(Paragraph(
        "Практическое руководство для владельцев сайтов, интернет-магазинов и онлайн-бизнеса. "
        "Как пройти круглосуточный ИИ-мониторинг Роскомнадзора, избежать блокировок и штрафов от 150 000 ₽ до 18 000 000 ₽.",
        style_doc_desc
    ))

    # 3. Readiness Bar & Risk Metrics
    legal = audit_data.get("legal", {})
    passed = legal.get("passed", 0)
    total = legal.get("total", 27)
    percent = legal.get("percent", 0)
    risk_level = legal.get("overall_risk", "Высокий риск")
    fine_form = legal.get("fine_form", "до 700 000 ₽")
    fine_loc = legal.get("fine_loc", "до 18 000 000 ₽")

    readiness_header_data = [[
        Paragraph("<b>ГОТОВНОСТЬ ВАШЕГО САЙТА К ПРОВЕРКАМ:</b>", ParagraphStyle('RHead', fontName=f_bold, fontSize=10, textColor=colors.HexColor("#1e293b"))),
        Paragraph(f"<b>{passed} / {total} выполнено ({percent}%)</b>", ParagraphStyle('RVal', fontName=f_bold, fontSize=11, textColor=colors.HexColor("#2563eb"), alignment=2))
    ]]
    readiness_header_table = Table(readiness_header_data, colWidths=[108 * mm, 70 * mm])
    readiness_header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(readiness_header_table)
    story.append(Spacer(1, 4))

    # 3 Metrics Row
    metrics_data = [
        [
            Paragraph("<font size=7 color='#64748b'>УРОВЕНЬ РИСКА</font><br/><b>" + risk_level + "</b>", ParagraphStyle('M1', fontName=f_bold, fontSize=10, textColor=colors.HexColor(legal.get("risk_color", "#ef4444")))),
            Paragraph("<font size=7 color='#64748b'>ШТРАФ ЗА ФОРМУ</font><br/><b>" + fine_form + "</b>", ParagraphStyle('M2', fontName=f_bold, fontSize=10, textColor=colors.HexColor("#0f172a"))),
            Paragraph("<font size=7 color='#64748b'>ШТРАФ ЗА ЛОКАЛИЗАЦИЮ</font><br/><b>" + fine_loc + "</b>", ParagraphStyle('M3', fontName=f_bold, fontSize=10, textColor=colors.HexColor("#0f172a")))
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[59.3 * mm, 59.3 * mm, 59.3 * mm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ffffff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('LINEAFTER', (0,0), (1,0), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 6))

    # Reality of 2026 Callout Box
    callout_text = (
        "<b>Реальность 2026 года:</b> Роскомнадзор внедрил круглосуточное автоматическое сканирование нейросетями. "
        "ИИ-боты находят скрытые счетчики Google Analytics, пиксели Meta, отсутствие политики в футере и предустановленные галочки. "
        "Инспектору передается готовый протокол с дедлайном на устранение всего 10 дней."
    )
    callout_data = [[Paragraph(callout_text, ParagraphStyle('Callout', fontName=f_reg, fontSize=8, leading=11, textColor=colors.HexColor("#7f1d1d")))]]
    callout_table = Table(callout_data, colWidths=[178 * mm])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fef2f2")),
        ('LINELEFT', (0,0), (0,0), 3, colors.HexColor("#dc2626")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#fecaca")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 8))

    # 4. Detailed Legal Blocks (1 to 7)
    blocks = legal.get("blocks", [])
    for block in blocks:
        block_items = []
        b_title = block.get("block_title", "")
        first_item = block["items"][0] if block.get("items") else {}
        b_fine = first_item.get("fine_info", "")

        b_head_table = Table([[
            Paragraph(f"<b>{b_title}</b>", style_block_title),
            Paragraph(f"<font color='#dc2626'>{b_fine}</font>", style_fine_tag)
        ]], colWidths=[110 * mm, 68 * mm])
        b_head_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        block_items.append(b_head_table)
        block_items.append(Spacer(1, 2))

        for it in block.get("items", []):
            st = it.get("status", "passed")
            if st == "passed":
                status_symbol = "<font color='#16a34a' size=9><b>[OK]</b></font>"
                bg_color = colors.HexColor("#ffffff")
            elif st == "warning":
                status_symbol = "<font color='#d97706' size=9><b>[!]</b></font>"
                bg_color = colors.HexColor("#fffbeb")
            else:
                status_symbol = "<font color='#dc2626' size=9><b>[X]</b></font>"
                bg_color = colors.HexColor("#fef2f2")

            content = (
                f"<b>{it.get('title')}</b> &nbsp;<font size=7 color='#64748b'>({it.get('law_ref')})</font><br/>"
                f"<font size=8 color='#334155'>{it.get('details')}</font><br/>"
                f"<font size=8 color='#0284c7'><b>Действие:</b> {it.get('tilda_fix')}</font>"
            )

            it_table = Table([[
                Paragraph(status_symbol, ParagraphStyle('Sym', fontName=f_bold, alignment=1)),
                Paragraph(content, style_item_title)
            ]], colWidths=[14 * mm, 164 * mm])
            it_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg_color),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            block_items.append(it_table)
            block_items.append(Spacer(1, 2))

        block_items.append(Spacer(1, 5))
        story.append(KeepTogether(block_items))

    # 5. Marketing and UX Conversion Block
    marketing = audit_data.get("marketing", {})
    m_checks = marketing.get("checks", [])
    if m_checks:
        m_items = []
        m_head_table = Table([[
            Paragraph("<b>8. Маркетинг и конверсия: почему сайт теряет клиентов</b>", style_block_title),
            Paragraph(f"<font color='#2563eb'>Оценка конверсии: {marketing.get('score', 0)}/100</font>", style_fine_tag)
        ]], colWidths=[112 * mm, 66 * mm])
        m_head_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#bfdbfe")),
        ]))
        m_items.append(m_head_table)
        m_items.append(Spacer(1, 2))

        for mc in m_checks:
            st = mc.get("status", "passed")
            if st == "passed":
                status_symbol = "<font color='#16a34a' size=9><b>[OK]</b></font>"
                bg_color = colors.HexColor("#ffffff")
            elif st == "warning":
                status_symbol = "<font color='#d97706' size=9><b>[!]</b></font>"
                bg_color = colors.HexColor("#fffbeb")
            else:
                status_symbol = "<font color='#dc2626' size=9><b>[X]</b></font>"
                bg_color = colors.HexColor("#fef2f2")

            m_content = (
                f"<b>{mc.get('title')}</b> &nbsp;<font size=7 color='#64748b'>({mc.get('impact')})</font><br/>"
                f"<font size=8 color='#334155'>{mc.get('details')}</font><br/>"
                f"<font size=8 color='#0284c7'><b>Рекомендация:</b> {mc.get('tilda_fix')}</font>"
            )

            m_row = Table([[
                Paragraph(status_symbol, ParagraphStyle('MSym', fontName=f_bold, alignment=1)),
                Paragraph(m_content, style_item_title)
            ]], colWidths=[14 * mm, 164 * mm])
            m_row.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg_color),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            m_items.append(m_row)
            m_items.append(Spacer(1, 2))

        m_items.append(Spacer(1, 6))
        story.append(KeepTogether(m_items))

    # 6. Final CTA Box (100% Clickable Links, clean layout)
    cta_title = Paragraph(
        "<b>Нужен аудит вашего сайта под ключ?</b>",
        ParagraphStyle('CTATitle', fontName=f_bold, fontSize=12, textColor=colors.HexColor("#0f172a"), alignment=1)
    )
    cta_body = Paragraph(
        "Проверим ваш сайт на скрытые зарубежные счетчики, соответствие формам сбора данных и требованиям реестра Роскомнадзора. "
        "Устраним уязвимости до официальной проверки.<br/><br/>"
        "• Telegram-канал: <a href='https://t.me/yanv_tg' color='#2563eb'><u><b>@yanv_tg</b></u></a> (разборы сайтов и чек-листы)<br/>"
        "• Личная связь и экспресс-аудит: <a href='https://t.me/yanvtg' color='#2563eb'><u><b>@yanvtg</b></u></a>",
        ParagraphStyle('CTABody', fontName=f_reg, fontSize=9, leading=14, textColor=colors.HexColor("#334155"), alignment=1)
    )
    cta_box = Table([[cta_title], [cta_body]], colWidths=[178 * mm])
    cta_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(KeepTogether([cta_box]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
