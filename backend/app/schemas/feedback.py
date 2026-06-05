from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FeedbackType
from app.schemas.common import ORMModel
from app.schemas.user import UserOut


class FeedbackCreate(BaseModel):
    analysis_id: int | None = None
    feedback_type: FeedbackType
    comment: str | None = Field(default=None, max_length=4000)


class FeedbackOut(ORMModel):
    id: int
    study_id: int
    analysis_id: int | None
    feedback_type: FeedbackType
    comment: str | None
    author: UserOut
    created_at: datetime
