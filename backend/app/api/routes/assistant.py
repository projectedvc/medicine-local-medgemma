import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.study import Study
from app.models.user import User
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.services.access import can_view_study
from app.services.groq_assistant import ask_medai

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantResponse)
async def chat(
    payload: AssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantResponse:
    study_context: str | None = None
    if payload.study_id is not None:
        study = db.get(Study, payload.study_id)
        if not study:
            raise HTTPException(status_code=404, detail="Исследование не найдено")
        if not can_view_study(current_user, study):
            raise HTTPException(status_code=403, detail="Нет доступа к исследованию")
        study_context = (
            f"Номер: {study.accession_number}; пациент: {study.patient_code}; тип: {study.study_type}; "
            f"статус: {study.status.value}; клиническая заметка: {study.clinical_note or 'не указана'}"
        )

    try:
        message = await ask_medai(
            [item.model_dump() for item in payload.messages],
            lang=payload.lang,
            study_context=study_context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="MedAI временно недоступен") from exc
    return AssistantResponse(message=message)
