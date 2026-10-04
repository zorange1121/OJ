from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from model import User
from services.auth import decode_access_token
from services.errors import InvalidCredentialsError


def _user_id_from_token(token: str, db: Session) -> int:
    try:
        user_id = decode_access_token(token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user_id


def get_current_user_id(
    authorization: str = Header("", description="Bearer <JWT access token> from POST /api/auth/login"),
    db: Session = Depends(get_db),
) -> int:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    return _user_id_from_token(token, db)


def get_current_user_id_from_query_token(token: str, db: Session) -> int:
    return _user_id_from_token(token, db)


def require_admin(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> int:
    user = db.get(User, user_id)
    if user is None or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user_id
