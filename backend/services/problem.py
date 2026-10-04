import zipfile
from io import BytesIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from model import Problem, ProblemData, ProblemTestCase, User
from schemas import ProblemDetail, ProblemListItem, ProblemTestCaseIn

from .errors import InvalidTestDataError, NotFoundError
from .testdata import validate_archive
from settings import MAX_UPLOAD_BYTES
import math

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "problem_data"


def list_problems(db: Session) -> list[ProblemListItem]:
    problems = db.scalars(select(Problem)).all()
    return [ProblemListItem.model_validate(p) for p in problems]


def get_problem(db: Session, problem_id: int) -> ProblemDetail:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise NotFoundError(f"Problem {problem_id} not found")
    return ProblemDetail.model_validate(problem)


def create_problem(
    db: Session,
    admin_id: int,
    name: str,
    description: str,
    time_limit: float,
    points: float,
    testcases: list[ProblemTestCaseIn],
    zip_bytes: bytes,
) -> ProblemDetail:
    if not math.isfinite(time_limit) or not 0 < time_limit <= 60:
        raise InvalidTestDataError("Time limit must be between 0 and 60 seconds")
    if not math.isfinite(points) or points <= 0 or sum(c.points for c in testcases) != points:
        raise InvalidTestDataError("Positive total points must equal the sum of test case points")
    if len(zip_bytes) > MAX_UPLOAD_BYTES:
        raise InvalidTestDataError("Test archive must be at most 8 MiB")
    if not zipfile.is_zipfile(BytesIO(zip_bytes)):
        raise InvalidTestDataError("Uploaded file is not a valid zip archive")

    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            validate_archive(archive, testcases)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise InvalidTestDataError("Cannot read test archive") from exc

    admin = db.get(User, admin_id)

    problem = Problem(
        name=name,
        description=description,
        time_limit=time_limit,
        points=points,
        user_count=0,
        ac_rate=0.0,
    )
    problem.authors.append(admin)
    created_path = None
    try:
        db.add(problem)
        db.flush()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = DATA_DIR / f"{problem.id}.zip"
        with zip_path.open("xb") as output:
            created_path = zip_path
            output.write(zip_bytes)
        problem_data = ProblemData(problem_id=problem.id, zipfile=str(zip_path))
        db.add(problem_data)
        db.flush()
        for case in testcases:
            db.add(
                ProblemTestCase(
                    problem_data_id=problem_data.id,
                    input_file=case.input_file,
                    output_file=case.output_file,
                    points=case.points,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        if created_path is not None:
            created_path.unlink(missing_ok=True)
        raise
    db.refresh(problem)

    return ProblemDetail.model_validate(problem)
