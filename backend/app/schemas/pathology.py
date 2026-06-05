from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PathologyCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=160)
    signs: str = Field(min_length=5)
    report_template: str = Field(min_length=5)
    examples: str | None = None
    references: str | None = None


class PathologyOut(ORMModel):
    id: int
    slug: str
    title: str
    signs: str
    report_template: str
    examples: str | None
    references: str | None
    updated_at: datetime
