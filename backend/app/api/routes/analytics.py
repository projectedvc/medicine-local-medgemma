from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.ai import AIAnalysis
from app.models.enums import AIJobStatus, Role
from app.models.feedback import Feedback
from app.models.study import Study
from app.models.user import User
from app.schemas.analytics import AnalyticsOverview

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.analyst, Role.expert)),
) -> AnalyticsOverview:
    by_status = {
        status: count
        for status, count in db.query(Study.status, func.count(Study.id)).group_by(Study.status).all()
    }
    feedback_by_type = {
        feedback_type: count
        for feedback_type, count in db.query(Feedback.feedback_type, func.count(Feedback.id)).group_by(Feedback.feedback_type).all()
    }
    avg_confidence = (
        db.query(func.avg(AIAnalysis.confidence))
        .filter(AIAnalysis.status == AIJobStatus.completed, AIAnalysis.confidence.is_not(None))
        .scalar()
    )
    return AnalyticsOverview(
        studies_by_status={str(key.value if hasattr(key, "value") else key): value for key, value in by_status.items()},
        studies_total=db.query(func.count(Study.id)).scalar() or 0,
        ai_completed=db.query(func.count(AIAnalysis.id)).filter(AIAnalysis.status == AIJobStatus.completed).scalar() or 0,
        ai_failed=db.query(func.count(AIAnalysis.id)).filter(AIAnalysis.status == AIJobStatus.failed).scalar() or 0,
        ai_average_confidence=float(avg_confidence) if avg_confidence is not None else None,
        feedback_by_type={str(key.value if hasattr(key, "value") else key): value for key, value in feedback_by_type.items()},
    )
