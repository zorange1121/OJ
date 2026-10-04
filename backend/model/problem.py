from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

problem_authors = Table(
    "problem_authors",
    Base.metadata,
    Column("problem_id", ForeignKey("problems.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    time_limit: Mapped[float] = mapped_column(Float)
    points: Mapped[float] = mapped_column(Float)
    user_count: Mapped[int] = mapped_column(Integer, default=0)
    ac_rate: Mapped[float] = mapped_column(Float, default=0.0)

    authors: Mapped[list["User"]] = relationship(
        secondary=problem_authors, back_populates="authored_problems"
    )
    data: Mapped["ProblemData"] = relationship(back_populates="problem", uselist=False)
    submissions: Mapped[list["Submission"]] = relationship(back_populates="problem")
    user_scores: Mapped[list["UserProblemScore"]] = relationship(back_populates="problem")


class ProblemData(Base):

    __tablename__ = "problem_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), unique=True)
    zipfile: Mapped[str] = mapped_column(String)

    problem: Mapped["Problem"] = relationship(back_populates="data")
    test_cases: Mapped[list["ProblemTestCase"]] = relationship(back_populates="problem_data")


class ProblemTestCase(Base):
    __tablename__ = "problem_test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_data_id: Mapped[int] = mapped_column(ForeignKey("problem_data.id"))
    input_file: Mapped[str] = mapped_column(String)
    output_file: Mapped[str] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer)

    problem_data: Mapped["ProblemData"] = relationship(back_populates="test_cases")
