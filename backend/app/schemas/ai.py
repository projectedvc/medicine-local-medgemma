from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AIJobStatus, FindingClass
from app.schemas.common import ORMModel


DISCLAIMER = "Результат является предварительной подсказкой. Окончательное решение принимает только врач"


class AIAnalysisOut(ORMModel):
    id: int
    study_id: int
    status: AIJobStatus
    predicted_class: FindingClass | None
    raw_predicted_label: str | None
    confidence: float | None
    threshold: float
    hidden_due_low_confidence: bool
    warning: str | None
    probabilities_json: str | None
    heatmap_path: str | None
    model_version: str
    dataset_version: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    disclaimer: str = DISCLAIMER


class RunAIRequest(BaseModel):
    wait: bool = True
    auto: bool = False
