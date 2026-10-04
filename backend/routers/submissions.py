from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import SubmissionCreate, SubmissionCreateResponse, SubmissionDetail
from model import User
from services import queue as queue_service
from services import submissions as submissions_service

from .deps import get_current_user_id
import logging
import pika

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionCreateResponse)
def create_submission(
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> SubmissionCreateResponse:
    response = submissions_service.create_submission(db, user_id, data)
    try:
        queue_service.publish_submission(response.id)
    except (pika.exceptions.AMQPError, OSError):
        logging.getLogger(__name__).exception("Submission %s queued in DB; broker unavailable", response.id)
    return response


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission(submission_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)) -> SubmissionDetail:
    result = submissions_service.get_submission(db, submission_id)
    if result.user_id != user_id and not db.get(User, user_id).is_admin:
        raise HTTPException(status_code=403, detail="Submission access denied")
    return result
