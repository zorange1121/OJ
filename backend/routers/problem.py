from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from database import get_db
from schemas import ProblemDetail, ProblemListItem, ProblemTestCaseIn
from services import problem as problem_service

from .deps import require_admin
from settings import MAX_UPLOAD_BYTES

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=list[ProblemListItem])
def list_problems(db: Session = Depends(get_db)) -> list[ProblemListItem]:
    return problem_service.list_problems(db)


@router.get("/{problem_id}", response_model=ProblemDetail)
def get_problem(problem_id: int, db: Session = Depends(get_db)) -> ProblemDetail:
    return problem_service.get_problem(db, problem_id)


@router.post("", response_model=ProblemDetail)
def create_problem(
    name: str = Form(..., min_length=1, max_length=200),
    description: str = Form(..., max_length=100000),
    time_limit: float = Form(...),
    points: float = Form(...),
    testcases: str = Form(..., description="JSON list of {input_file, output_file, points}"),
    zipfile: UploadFile = File(..., description="Zip archive containing the input_file/output_file pairs"),
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProblemDetail:
    try:
        parsed_testcases = TypeAdapter(list[ProblemTestCaseIn]).validate_json(testcases)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid testcases: {exc}") from exc

    return problem_service.create_problem(
        db,
        admin_id=admin_id,
        name=name,
        description=description,
        time_limit=time_limit,
        points=points,
        testcases=parsed_testcases,
        zip_bytes=zipfile.file.read(MAX_UPLOAD_BYTES + 1),
    )
