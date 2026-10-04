from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import LoginRequest, LoginResponse
from services import auth as auth_service
from services.login_limit import check_login_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    check_login_limit(data.username)
    return auth_service.login(db, data.username, data.password)
