from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import AIJobStatus, FindingClass
from app.schemas.common import ORMModel


DISCLAIMER = "Результат является предварительной подсказкой. Окончательное решение принимает только врач"


class AIAnalysisOut(ORMModel):
    id: int
    study_id: int
    status: AIJobStatus
    predicted_class: FindingClass | None
    raw_predicted_label: str | None
    ai_text: str | None = None
    evidence: list[str] = Field(default_factory=list)
    localization_bbox: list[float] | None = None
    localization_status: Literal[
        "available",
        "not_applicable",
        "unavailable_unvalidated",
        "unavailable_class_only",
    ] = "unavailable_class_only"
    model_quality_status: Literal["experimental", "candidate", "validated", "unvalidated"] = "unvalidated"
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
    lang: str = "ru"
    model_variant: Literal["base", "pneumonia_v1", "rsna_v2"] = "base"
