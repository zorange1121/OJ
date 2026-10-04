from pydantic import BaseModel, Field

from .users import UserOut


class ProblemListItem(BaseModel):
    id: int
    name: str
    points: float
    user_count: int
    ac_rate: float

    model_config = {"from_attributes": True}


class ProblemTestCaseIn(BaseModel):
    input_file: str = Field(min_length=1, max_length=200)
    output_file: str = Field(min_length=1, max_length=200)
    points: int = Field(gt=0, le=100000)


class ProblemDetail(BaseModel):
    id: int
    name: str
    description: str
    time_limit: float
    points: float
    user_count: int
    ac_rate: float
    authors: list[UserOut]

    model_config = {"from_attributes": True}
