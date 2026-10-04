from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, default="")
    is_admin: Mapped[bool] = mapped_column(default=False)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")
    problem_scores: Mapped[list["UserProblemScore"]] = relationship(back_populates="user")
    authored_problems: Mapped[list["Problem"]] = relationship(
        secondary="problem_authors", back_populates="authors"
    )
