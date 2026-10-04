from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import LeaderboardEntry, UserOut, UserProgress
from schemas.auth import UserCreateRequest
from services import auth as auth_service
from services import users as users_service
from services.errors import UsernameTakenError

from .deps import require_admin

router = APIRouter(prefix="/api", tags=["users"])


@router.post("/users", response_model=UserOut)
def create_user(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    _admin_id: int = Depends(require_admin),
) -> UserOut:
    try:
        user = auth_service.create_user(db, data.username, data.password, data.is_admin)
    except UsernameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserOut.model_validate(user)


@router.get("/users/{user_id}/progress", response_model=UserProgress)
def get_user_progress(user_id: int, db: Session = Depends(get_db)) -> UserProgress:
    return users_service.get_user_progress(db, user_id)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)) -> list[LeaderboardEntry]:
    return users_service.get_leaderboard(db)
