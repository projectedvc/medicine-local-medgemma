from typing import Literal

from pydantic import BaseModel, Field


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class AssistantRequest(BaseModel):
    messages: list[AssistantMessage] = Field(min_length=1, max_length=20)
    study_id: int | None = None
    lang: Literal["kk", "ru", "en"] = "ru"


class AssistantResponse(BaseModel):
    message: str
