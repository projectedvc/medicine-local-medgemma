from datetime import datetime, timezone
import json

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AIJobStatus, FindingClass


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), nullable=False, index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[AIJobStatus] = mapped_column(Enum(AIJobStatus), default=AIJobStatus.queued, index=True)
    predicted_class: Mapped[FindingClass | None] = mapped_column(Enum(FindingClass), nullable=True, index=True)
    raw_predicted_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    hidden_due_low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    probabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    heatmap_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    study = relationship("Study", back_populates="analyses")
    requested_by = relationship("User")

    @property
    def ai_text(self) -> str | None:
        """Текстовый вывод AI-модели из raw_response_json."""
        try:
            data = json.loads(self.raw_response_json or "{}")
        except Exception:
            return None

        return (
            data.get("ai_text")
            or data.get("impression")
            or data.get("raw_response")
            or data.get("response")
            or data.get("text")
        )

    @property
    def evidence(self) -> list[str]:
        """Return only concise, non-empty visual findings from the model payload."""
        try:
            data = json.loads(self.raw_response_json or "{}")
        except Exception:
            return []
        evidence = data.get("evidence")
        if not isinstance(evidence, list):
            return []
        return [str(item).strip() for item in evidence[:3] if str(item).strip()]

    @property
    def localization_bbox(self) -> list[float] | None:
        """Expose a box only when a validated localization model produced it."""
        try:
            data = json.loads(self.raw_response_json or "{}")
        except Exception:
            return None
        localization = data.get("localization")
        if not isinstance(localization, dict) or localization.get("validated") is not True:
            return None
        bbox = localization.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            return None
        try:
            values = [float(value) for value in bbox]
        except (TypeError, ValueError):
            return None
        x1, y1, x2, y2 = values
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            return None
        return values

    @property
    def localization_status(self) -> str:
        if self.localization_bbox:
            return "available"
        try:
            data = json.loads(self.raw_response_json or "{}")
        except Exception:
            return "unavailable_unvalidated"
        localization = data.get("localization")
        reason = localization.get("reason") if isinstance(localization, dict) else None
        if reason in {"normal_study", "no_localizable_pneumonia", "not_applicable"}:
            return "not_applicable"
        if reason == "class_only_training_data":
            return "unavailable_class_only"
        return "unavailable_unvalidated"

    @property
    def model_quality_status(self) -> str:
        if self.model_version == "medai-pneumonia-v1":
            return "experimental"
        if self.model_version == "medai-rsna-pneumonia-v2":
            try:
                data = json.loads(self.raw_response_json or "{}")
            except Exception:
                return "candidate"
            return "validated" if data.get("quality_gate_passed") is True else "candidate"
        return "unvalidated"
