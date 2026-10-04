from sqlalchemy import func, select
from sqlalchemy.orm import Session

from model import Problem, User
from model import UserProblemScore as UserProblemScoreModel
from schemas import LeaderboardEntry, UserOut, UserProgress
from schemas.users import UserProblemScore as UserProblemScoreOut

from .errors import NotFoundError


def get_user(db: Session, user_id: int) -> UserOut:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return UserOut.model_validate(user)


def get_user_progress(db: Session, user_id: int) -> UserProgress:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")

    rows = db.execute(
        select(UserProblemScoreModel, Problem)
        .join(Problem, UserProblemScoreModel.problem_id == Problem.id)
        .where(UserProblemScoreModel.user_id == user_id)
    ).all()

    problems = [
        UserProblemScoreOut(
            problem_id=problem.id,
            problem_name=problem.name,
            points=problem.points,
            max_score=score.max_score,
        )
        for score, problem in rows
    ]
    total_score = sum(p.max_score for p in problems)

    return UserProgress(
        user_id=user.id,
        username=user.username,
        total_score=total_score,
        problems=problems,
    )


def get_leaderboard(db: Session) -> list[LeaderboardEntry]:
    total_score = func.coalesce(func.sum(UserProblemScoreModel.max_score), 0)
    rows = db.execute(
        select(User, total_score.label("total_score"))
        .outerjoin(UserProblemScoreModel, UserProblemScoreModel.user_id == User.id)
        .group_by(User.id)
        .order_by(total_score.desc())
    ).all()

    return [
        LeaderboardEntry(rank=i + 1, user_id=user.id, username=user.username, total_score=score)
        for i, (user, score) in enumerate(rows)
    ]
