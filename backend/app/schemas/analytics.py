from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    studies_by_status: dict[str, int]
    studies_total: int
    ai_completed: int
    ai_failed: int
    ai_average_confidence: float | None
    feedback_by_type: dict[str, int]
