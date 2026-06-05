from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.studies import ensure_study_access, get_study_or_404
from app.db.session import get_db
from app.models.enums import AuditAction, Role
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackOut
from app.services.audit import write_audit

router = APIRouter(prefix="/studies/{study_id}/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    study_id: int,
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Feedback:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if current_user.role not in {Role.radiologist, Role.physician, Role.expert}:
        raise HTTPException(status_code=403, detail="Нет права оставлять медицинскую обратную связь")
    item = Feedback(
        study_id=study.id,
        analysis_id=payload.analysis_id,
        author_id=current_user.id,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    write_audit(
        db,
        action=AuditAction.create_feedback,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"feedback_id": item.id, "type": item.feedback_type.value},
        request=request,
    )
    return item


@router.get("", response_model=list[FeedbackOut])
def list_feedback(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Feedback]:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    return db.query(Feedback).filter(Feedback.study_id == study.id).order_by(Feedback.created_at.desc()).all()
