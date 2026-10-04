from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    is_admin: bool


class UserCreateRequest(LoginRequest):
    is_admin: bool = False
