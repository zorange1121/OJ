from pydantic import BaseModel


class UserBase(BaseModel):
    username: str


class UserOut(UserBase):
    id: int

    model_config = {"from_attributes": True}


class UserProblemScore(BaseModel):
    problem_id: int
    problem_name: str
    points: float
    max_score: float


class UserProgress(BaseModel):
    user_id: int
    username: str
    total_score: float
    problems: list[UserProblemScore]


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    total_score: float
