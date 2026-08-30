from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Node(StrictModel):
    key: str = Field(min_length=1, max_length=90)
    level: Literal["subject", "unit", "topic", "subtopic"]
    parent: str | None = Field(None, max_length=90)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field("", max_length=500)
    learning_outcome: str = Field("", max_length=500)
    sequence: int = Field(ge=1, le=100000, strict=True)


class StartReview(StrictModel):
    subject_id: int | None = None


class SaveReview(StrictModel):
    version: int = Field(ge=1)
    summary: str = Field(max_length=1000)
    nodes: list[Node] = Field(max_length=5000)


class ReviewAction(StrictModel):
    version: int = Field(ge=1)
    action: Literal["submit", "withdraw", "approve", "request_changes", "reject"]
    comment: str = Field("", max_length=2000)


class WorkbookPreview(StrictModel):
    version: int = Field(ge=1)
    metadata: dict[str, str]
    sheets: dict[str, list[dict]]


class SubjectReviewAction(StrictModel):
    version: int = Field(ge=1)
    subject_key: str = Field(min_length=1, max_length=90)
    action: Literal["assign", "unassign", "request", "save", "recommend", "approve", "return"]
    reviewer_id: int | None = None
    comment: str = Field("", max_length=2000)
    nodes: list[Node] | None = Field(None, max_length=5000)


class ResetSyllabus(StrictModel):
    version: int = Field(ge=1)
    course_code: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=5, max_length=1000)
    cancel_requests: bool = False
