from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.user import UserOut


class CRMStudyOut(ORMModel):
    id: int
    accession_number: str
    patient_code: str
    study_type: str
    status: str


class CRMActivityOut(ORMModel):
    id: int
    activity_type: str
    content: str
    author: UserOut
    created_at: datetime


class CRMActivityCreate(BaseModel):
    activity_type: str = Field(default="note", max_length=40)
    content: str = Field(min_length=1, max_length=4000)


class CRMRecordCreate(BaseModel):
    patient_code: str = Field(min_length=2, max_length=80)
    contact_type: str = Field(default="consultation", max_length=80)
    status: str = Field(default="active", max_length=80)
    priority: str = Field(default="normal", max_length=40)
    summary: str = Field(min_length=2, max_length=240)
    note: str = Field(min_length=1, max_length=6000)
    next_step: str | None = Field(default=None, max_length=240)
    due_at: datetime | None = None
    participant_ids: list[int] = Field(default_factory=list, max_length=20)
    linked_study_ids: list[int] = Field(default_factory=list, max_length=20)


class CRMRecordUpdate(BaseModel):
    patient_code: str | None = Field(default=None, min_length=2, max_length=80)
    contact_type: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=80)
    priority: str | None = Field(default=None, max_length=40)
    summary: str | None = Field(default=None, min_length=2, max_length=240)
    note: str | None = Field(default=None, min_length=1, max_length=6000)
    next_step: str | None = Field(default=None, max_length=240)
    due_at: datetime | None = None
    participant_ids: list[int] | None = Field(default=None, max_length=20)
    linked_study_ids: list[int] | None = Field(default=None, max_length=20)


class CRMRecordOut(ORMModel):
    id: int
    patient_code: str
    contact_type: str
    status: str
    priority: str
    summary: str
    note: str
    next_step: str | None
    due_at: datetime | None
    created_by: UserOut
    updated_by: UserOut | None = None
    participants: list[UserOut] = Field(default_factory=list)
    studies: list[CRMStudyOut] = Field(default_factory=list)
    activities: list[CRMActivityOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
