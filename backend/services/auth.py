import time

import bcrypt
import jwt
from sqlalchemy.orm import Session

from model import User
from schemas import LoginResponse
from settings import JWT_SECRET

from .errors import InvalidCredentialsError, UsernameTakenError

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_SECONDS = 60 * 60 * 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_access_token(user_id: int) -> str:
    now = int(time.time())
    payload = {"user_id": user_id, "iat": now, "exp": now + JWT_EXPIRES_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "iat", "user_id"]})
    except jwt.PyJWTError as exc:
        raise InvalidCredentialsError("Invalid or expired token") from exc
    user_id = payload["user_id"]
    if type(user_id) is not int or user_id <= 0:
        raise InvalidCredentialsError("Invalid token subject")
    return user_id


def login(db: Session, username: str, password: str) -> LoginResponse:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid username or password")
    token = _create_access_token(user.id)
    return LoginResponse(
        access_token=token, token_type="bearer", user_id=user.id, username=user.username, is_admin=user.is_admin
    )


def create_user(db: Session, username: str, password: str, is_admin: bool = False) -> User:
    if db.query(User).filter(User.username == username).first() is not None:
        raise UsernameTakenError(f"Username '{username}' already exists")
    user = User(username=username, password_hash=hash_password(password), is_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
