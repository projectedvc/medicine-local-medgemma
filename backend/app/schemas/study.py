from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import StudyStatus
from app.schemas.common import ORMModel
from app.schemas.user import UserOut


class StudyCreate(BaseModel):
    patient_code: str = Field(min_length=2, max_length=80)
    study_type: str = Field(default="ОГК", max_length=64)
    clinical_note: str | None = Field(default=None, max_length=4000)
    assigned_radiologist_id: int | None = None


class StudyUpdate(BaseModel):
    patient_code: str | None = Field(default=None, min_length=2, max_length=80)
    study_type: str | None = Field(default=None, max_length=64)
    clinical_note: str | None = Field(default=None, max_length=4000)
    assigned_radiologist_id: int | None = None
    status: StudyStatus | None = None


class ImageFileOut(ORMModel):
    id: int
    original_filename: str
    content_type: str | None
    size_bytes: int
    file_format: str
    width: int | None
    height: int | None
    validation_status: str
    validation_message: str
    created_at: datetime


class StudyOut(ORMModel):
    id: int
    accession_number: str
    patient_code: str
    study_type: str
    clinical_note: str | None
    status: StudyStatus
    created_at: datetime
    updated_at: datetime
    uploader: UserOut
    assigned_radiologist: UserOut | None = None


class StudyDetail(StudyOut):
    images: list[ImageFileOut] = []
