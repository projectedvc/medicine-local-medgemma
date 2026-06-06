from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.studies import ensure_study_access, get_study_or_404
from app.db.session import get_db
from app.models.ai import AIAnalysis
from app.models.enums import AIJobStatus, AuditAction, Role, StudyStatus
from app.models.report import Report, ReportVersion
from app.models.user import User
from app.schemas.report import ReportConfirmRequest, ReportOut, ReportSaveRequest
from app.services.access import can_confirm_report, can_edit_report
from app.services.audit import write_audit
from app.services.reporting import build_ai_draft, export_report_docx, export_report_pdf

router = APIRouter(prefix="/studies/{study_id}/report", tags=["reports"])


def _get_or_create_report(db: Session, study_id: int) -> Report:
    report = db.query(Report).filter(Report.study_id == study_id).one_or_none()
    if report:
        return report
    report = Report(study_id=study_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _latest_completed_analysis(db: Session, study_id: int) -> AIAnalysis | None:
    return (
        db.query(AIAnalysis)
        .filter(AIAnalysis.study_id == study_id, AIAnalysis.status == AIJobStatus.completed)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )


def _final_text_is_ai_draft(report: Report) -> bool:
    final_text = (report.final_text or "").strip()
    ai_draft = (report.ai_draft_text or "").strip()
    return not final_text or final_text == ai_draft


def _sync_report_language_for_export(db: Session, study, report: Report, lang: str) -> None:
    if not _final_text_is_ai_draft(report):
        return
    analysis = _latest_completed_analysis(db, study.id)
    report.ai_draft_text = build_ai_draft(study, analysis, lang)
    report.ai_draft_created_at = datetime.now(timezone.utc)
    report.final_text = report.ai_draft_text


@router.get("", response_model=ReportOut)
def get_report(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    report = db.query(Report).filter(Report.study_id == study.id).one_or_none()
    return report or _get_or_create_report(db, study.id)


@router.post("/draft", response_model=ReportOut)
def create_draft(
    study_id: int,
    request: Request,
    lang: str = "ru",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if current_user.role not in {Role.radiologist, Role.physician, Role.expert}:
        raise HTTPException(status_code=403, detail="Нет права формировать черновик")
    analysis = _latest_completed_analysis(db, study.id)
    report = _get_or_create_report(db, study.id)
    previous_ai_draft = report.ai_draft_text
    report.ai_draft_text = build_ai_draft(study, analysis, lang)
    report.ai_draft_created_at = datetime.now(timezone.utc)
    if not report.final_text or report.final_text == previous_ai_draft:
        report.final_text = report.ai_draft_text
        report.edited_by_id = current_user.id
    report.versions.append(ReportVersion(editor_id=current_user.id, source="ai_draft", text=report.ai_draft_text))
    study.status = StudyStatus.draft_ready
    db.commit()
    db.refresh(report)
    write_audit(
        db,
        action=AuditAction.create_draft,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"report_id": report.id},
        request=request,
    )
    return report


@router.put("", response_model=ReportOut)
def save_report(
    study_id: int,
    payload: ReportSaveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if not can_edit_report(current_user, study):
        raise HTTPException(status_code=403, detail="Финальный текст может редактировать только рентгенолог или эксперт")
    report = _get_or_create_report(db, study.id)
    report.final_text = payload.final_text
    report.edited_by_id = current_user.id
    report.confirmed_by_id = None
    report.confirmed_at = None
    report.versions.append(ReportVersion(editor_id=current_user.id, source="doctor_final", text=payload.final_text))
    study.status = StudyStatus.draft_ready
    db.commit()
    db.refresh(report)
    write_audit(
        db,
        action=AuditAction.edit_report,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"report_id": report.id},
        request=request,
    )
    return report


@router.post("/confirm", response_model=ReportOut)
def confirm_report(
    study_id: int,
    payload: ReportConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if not can_confirm_report(current_user, study):
        raise HTTPException(status_code=403, detail="Подтверждать заключение может только рентгенолог или эксперт")
    if not payload.accept_responsibility:
        raise HTTPException(status_code=400, detail="Нужно вручную принять ответственность за финальный текст")
    report = db.query(Report).filter(Report.study_id == study.id).one_or_none()
    if not report or not report.final_text:
        raise HTTPException(status_code=400, detail="Сначала сохраните финальный текст заключения")
    report.confirmed_by_id = current_user.id
    report.confirmed_at = datetime.now(timezone.utc)
    study.status = StudyStatus.confirmed
    db.commit()
    db.refresh(report)
    write_audit(
        db,
        action=AuditAction.confirm_report,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"report_id": report.id},
        request=request,
    )
    return report


def _export_guard(db: Session, current_user: User, study_id: int) -> tuple:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    report = db.query(Report).filter(Report.study_id == study.id).one_or_none()
    if not report or not report.confirmed_at or not report.confirmed_by:
        raise HTTPException(status_code=400, detail="Экспорт доступен только для подтвержденного заключения")
    return study, report, report.confirmed_by


@router.get("/export/pdf")
def export_pdf(
    study_id: int,
    request: Request,
    lang: str = "ru",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    study, report, doctor = _export_guard(db, current_user, study_id)
    _sync_report_language_for_export(db, study, report, lang)
    path = export_report_pdf(study, report, doctor, lang)
    study.status = StudyStatus.exported
    db.commit()
    write_audit(db, action=AuditAction.export_report, user=current_user, entity_type="study", entity_id=study.id, details={"format": "pdf"}, request=request)
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.get("/export/docx")
def export_docx(
    study_id: int,
    request: Request,
    lang: str = "ru",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    study, report, doctor = _export_guard(db, current_user, study_id)
    _sync_report_language_for_export(db, study, report, lang)
    path = export_report_docx(study, report, doctor, lang)
    study.status = StudyStatus.exported
    db.commit()
    write_audit(db, action=AuditAction.export_report, user=current_user, entity_type="study", entity_id=study.id, details={"format": "docx"}, request=request)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=path.name)
