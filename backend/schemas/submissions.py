from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from settings import MAX_SOURCE_BYTES


class SubmissionStatus(str, Enum):
    PENDING = "Pending"
    COMPILING = "Compiling"
    RUNNING = "Running"
    ACCEPTED = "AC"
    WRONG_ANSWER = "WA"
    TIME_LIMIT_EXCEEDED = "TLE"
    MEMORY_LIMIT_EXCEEDED = "MLE"
    RUNTIME_ERROR = "RE"
    COMPILE_ERROR = "CE"


class SubmissionCreate(BaseModel):
    problem_id: int = Field(gt=0)
    source: str = Field(min_length=1, max_length=MAX_SOURCE_BYTES)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_SOURCE_BYTES or not value.strip() or "\x00" in value:
            raise ValueError("Source must be nonempty UTF-8 text, at most 128 KiB, without NUL bytes")
        return value


class SubmissionCreateResponse(BaseModel):
    id: int
    status: SubmissionStatus


class SubmissionDetail(BaseModel):
    id: int
    user_id: int
    problem_id: int
    time: float | None
    points: float | None
    status: SubmissionStatus
    source: str
    cycles: int | None
    compile_output: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
