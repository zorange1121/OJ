from sqlalchemy.orm import Session

from model import Problem, Submission, User
from fastapi import HTTPException
from sqlalchemy import select
from schemas import SubmissionCreate, SubmissionCreateResponse, SubmissionDetail
from schemas.submissions import SubmissionStatus

from .errors import NotFoundError


def create_submission(db: Session, user_id: int, data: SubmissionCreate) -> SubmissionCreateResponse:
    db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one()
    active_count = db.query(Submission).filter(Submission.user_id == user_id,
        Submission.status.in_([SubmissionStatus.PENDING, SubmissionStatus.COMPILING, SubmissionStatus.RUNNING])).count()
    if active_count >= 5:
        raise HTTPException(status_code=429, detail="At most 5 unfinished submissions per user")
    problem = db.get(Problem, data.problem_id)
    if problem is None:
        raise NotFoundError(f"Problem {data.problem_id} not found")

    submission = Submission(
        user_id=user_id,
        problem_id=data.problem_id,
        source=data.source,
        status=SubmissionStatus.PENDING,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return SubmissionCreateResponse(id=submission.id, status=submission.status)


def get_submission(db: Session, submission_id: int) -> SubmissionDetail:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise NotFoundError(f"Submission {submission_id} not found")
    return SubmissionDetail.model_validate(submission)
