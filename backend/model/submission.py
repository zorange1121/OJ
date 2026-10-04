from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from schemas.submissions import SubmissionStatus

from .base import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    time: Mapped[float | None] = mapped_column(Float, nullable=True)
    points: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.PENDING
    )
    source: Mapped[str] = mapped_column(Text)
    cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compile_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped["User"] = relationship(back_populates="submissions")
    problem: Mapped["Problem"] = relationship(back_populates="submissions")


class UserProblemScore(Base):
    __tablename__ = "user_problem_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    max_score: Mapped[int] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="problem_scores")
    problem: Mapped["Problem"] = relationship(back_populates="user_scores")
