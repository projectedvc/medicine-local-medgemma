from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.ai import AIAnalysis
from app.models.enums import FINDING_LABELS, FindingClass
from app.models.report import Report
from app.models.study import Study
from app.models.user import User


DISCLAIMER = "Результат является предварительной подсказкой. Окончательное решение принимает только врач"


TEMPLATES: dict[FindingClass, str] = {
    FindingClass.normal: "Свежих очагово-инфильтративных изменений на представленной рентгенограмме ОГК AI не выделил. Плевральные синусы без признаков свободной жидкости по предварительной оценке.",
    FindingClass.pneumonia: "AI отметил признаки, которые могут соответствовать инфильтративным изменениям легочной ткани. Необходимо врачебное сопоставление с клиникой, лабораторными данными и прямой оценкой снимка.",
    FindingClass.pleural_effusion: "AI отметил признаки, подозрительные на наличие жидкости в плевральной полости. Сторона, объем и клиническая значимость должны быть подтверждены врачом.",
    FindingClass.pneumothorax: "AI отметил признаки, подозрительные на пневмоторакс. Требуется приоритетная врачебная оценка изображения и клинического состояния пациента.",
    FindingClass.atelectasis: "AI отметил признаки возможного снижения объема участка легочной ткани/ателектаза. Требуется врачебная верификация по изображению.",
}


def build_ai_draft(study: Study, analysis: AIAnalysis | None) -> str:
    lines = [
        "AI-черновик описания ОГК",
        f"Исследование: {study.accession_number}",
        f"Код пациента: {study.patient_code}",
        "",
        f"ВАЖНО: {DISCLAIMER}.",
        "",
    ]
    if not analysis or analysis.status.value != "completed":
        lines.append("AI-анализ отсутствует или еще не завершен. Описание должно быть подготовлено врачом вручную.")
        return "\n".join(lines)

    if analysis.hidden_due_low_confidence or not analysis.predicted_class:
        lines.extend(
            [
                "Уверенность AI ниже установленного порога.",
                "Система не показывает диагностический класс. Требуется ручное описание врачом.",
            ]
        )
        return "\n".join(lines)

    label = FINDING_LABELS.get(analysis.predicted_class, analysis.predicted_class.value)
    confidence = f"{(analysis.confidence or 0) * 100:.1f}%"
    lines.extend(
        [
            f"Предварительная подсказка AI: {label}.",
            f"Уверенность AI: {confidence}.",
            "",
            TEMPLATES[analysis.predicted_class],
            "",
            "Финальное заключение врач должен отредактировать и подтвердить вручную.",
        ]
    )
    return "\n".join(lines)


def ensure_export_dir() -> Path:
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    return settings.export_dir


def _font_candidates() -> list[str]:
    candidates = []
    if settings.pdf_font_path:
        candidates.append(settings.pdf_font_path)
    candidates.extend(
        [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        ]
    )
    return candidates


def export_report_pdf(study: Study, report: Report, doctor: User) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    export_dir = ensure_export_dir()
    path = export_dir / f"study-{study.id}-report.pdf"
    font_name = "Helvetica"
    for candidate in _font_candidates():
        if Path(candidate).exists():
            pdfmetrics.registerFont(TTFont("ClinicalSans", candidate))
            font_name = "ClinicalSans"
            break

    styles = getSampleStyleSheet()
    styles["Title"].fontName = font_name
    styles["Normal"].fontName = font_name
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"Заключение {study.accession_number}")
    story = [
        Paragraph("Подтвержденное заключение", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Исследование: {study.accession_number}", styles["Normal"]),
        Paragraph(f"Код пациента: {study.patient_code}", styles["Normal"]),
        Paragraph(f"Подтвердил: {doctor.full_name}", styles["Normal"]),
        Paragraph(f"Дата экспорта: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]),
        Spacer(1, 12),
    ]
    for paragraph in (report.final_text or "").splitlines():
        story.append(Paragraph(paragraph or "&nbsp;", styles["Normal"]))
        story.append(Spacer(1, 6))
    doc.build(story)
    return path


def export_report_docx(study: Study, report: Report, doctor: User) -> Path:
    from docx import Document

    export_dir = ensure_export_dir()
    path = export_dir / f"study-{study.id}-report.docx"
    doc = Document()
    doc.add_heading("Подтвержденное заключение", level=1)
    doc.add_paragraph(f"Исследование: {study.accession_number}")
    doc.add_paragraph(f"Код пациента: {study.patient_code}")
    doc.add_paragraph(f"Подтвердил: {doctor.full_name}")
    doc.add_paragraph(f"Дата экспорта: {datetime.now(timezone.utc).isoformat()}")
    doc.add_paragraph("")
    for paragraph in (report.final_text or "").splitlines():
        doc.add_paragraph(paragraph)
    doc.save(path)
    return path
