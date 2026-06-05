from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.user import UserOut


class ReportOut(ORMModel):
    id: int
    study_id: int
    ai_draft_text: str | None
    ai_draft_created_at: datetime | None
    final_text: str | None
    edited_by: UserOut | None = None
    confirmed_by: UserOut | None = None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportSaveRequest(BaseModel):
    final_text: str = Field(min_length=5, max_length=20000)


class ReportConfirmRequest(BaseModel):
    accept_responsibility: bool
