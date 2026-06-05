import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.studies import ensure_study_access, get_study_or_404
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.ai import AIAnalysis
from app.models.enums import AIJobStatus, AuditAction, StudyStatus
from app.models.study import Study
from app.models.user import User
from app.schemas.ai import AIAnalysisOut, RunAIRequest
from app.services.access import can_run_ai
from app.services.ai_client import probabilities_to_json, run_ai_inference
from app.services.audit import write_audit

router = APIRouter(prefix="/studies/{study_id}/ai", tags=["ai"])


def _latest_image(study: Study):
    if not study.images:
        raise HTTPException(status_code=400, detail="Сначала загрузите снимок")
    return study.images[-1]


async def process_analysis(db: Session, analysis: AIAnalysis, study: Study) -> AIAnalysis:
    image = _latest_image(study)
    analysis.status = AIJobStatus.running
    study.status = StudyStatus.analyzing
    db.commit()
    try:
        result = await run_ai_inference(image.storage_path)
        hidden = result.confidence < settings.ai_confidence_threshold
        analysis.status = AIJobStatus.completed
        analysis.raw_predicted_label = result.raw_predicted_label
        analysis.predicted_class = None if hidden else result.predicted_class
        analysis.confidence = result.confidence
        analysis.hidden_due_low_confidence = hidden
        analysis.warning = (
            "Уверенность AI ниже установленного порога. Диагностический класс скрыт, требуется ручная оценка врача."
            if hidden
            else result.warning
        )
        analysis.probabilities_json = probabilities_to_json(result.probabilities)
        analysis.heatmap_path = result.heatmap_path
        analysis.raw_response_json = json.dumps(result.raw_response, ensure_ascii=False)
        analysis.completed_at = datetime.now(timezone.utc)
        study.status = StudyStatus.ai_completed
    except Exception as exc:
        analysis.status = AIJobStatus.failed
        analysis.error_message = str(exc)
        analysis.completed_at = datetime.now(timezone.utc)
        study.status = StudyStatus.ready_for_analysis
    db.commit()
    db.refresh(analysis)
    return analysis


async def process_analysis_by_id(analysis_id: int) -> None:
    db = SessionLocal()
    try:
        analysis = db.get(AIAnalysis, analysis_id)
        if not analysis:
            return
        study = get_study_or_404(db, analysis.study_id)
        await process_analysis(db, analysis, study)
    finally:
        db.close()


@router.post("/run", response_model=AIAnalysisOut)
async def run_ai(
    study_id: int,
    payload: RunAIRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIAnalysis:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if not can_run_ai(current_user, study):
        raise HTTPException(status_code=403, detail="Нет права запускать AI-анализ")
    _latest_image(study)
    analysis = AIAnalysis(
        study_id=study.id,
        requested_by_id=current_user.id,
        status=AIJobStatus.queued,
        threshold=settings.ai_confidence_threshold,
        model_version=settings.ai_model_version,
        dataset_version=settings.ai_dataset_version,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    write_audit(
        db,
        action=AuditAction.run_ai,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"analysis_id": analysis.id, "auto": payload.auto, "wait": payload.wait},
        request=request,
    )
    if payload.wait:
        return await process_analysis(db, analysis, study)
    background_tasks.add_task(process_analysis_by_id, analysis.id)
    return analysis


@router.get("", response_model=list[AIAnalysisOut])
def list_ai_results(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIAnalysis]:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    return (
        db.query(AIAnalysis)
        .filter(AIAnalysis.study_id == study.id)
        .order_by(AIAnalysis.created_at.desc())
        .all()
    )
