import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import SessionLocal
from model import Problem, ProblemTestCase, Submission, User, UserProblemScore
from schemas.submissions import SubmissionStatus
from .testdata import parse_key_values, validate_archive
from .assembly import prepare_source, validate_cod
from .diagnostics import compilation_feedback

logger = logging.getLogger(__name__)
DOCKER_IMAGE = os.environ.get("JUDGE_DOCKER_IMAGE", "pic-judge")
DOCKER_BIN = os.environ.get("DOCKER_BIN", "docker")
PIC_MODEL = "p18f4520"
DOCKER_MEMORY = os.environ.get("JUDGE_DOCKER_MEMORY", "256m")
DOCKER_CPUS = os.environ.get("JUDGE_DOCKER_CPUS", "1")
DOCKER_PIDS_LIMIT = os.environ.get("JUDGE_DOCKER_PIDS_LIMIT", "64")
DATA_DIR = Path(os.environ.get("JUDGE_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "submissions")))
COMPILE_TIMEOUT = 15
TOTAL_TIMEOUT = 300
LEASE_SECONDS = 600
ACTIVE_STATUSES = (SubmissionStatus.PENDING, SubmissionStatus.COMPILING, SubmissionStatus.RUNNING)


class _JudgeFailure(Exception):
    pass


class SandboxError(RuntimeError):
    pass


def cleanup_stale_workdirs() -> None:
    if not DATA_DIR.exists():
        return
    cutoff = time.time() - 2 * LEASE_SECONDS
    with SessionLocal() as db:
        leased = {row[0] for row in db.query(Submission.id).filter(Submission.lease_until >= time.time()).all()}
    for path in DATA_DIR.iterdir():
        match = re.fullmatch(r"(\d+)-[a-z0-9_]{8}", path.name)
        if not match or path.is_symlink() or not path.is_dir() or int(match[1]) in leased:
            continue
        if path.resolve().parent != DATA_DIR.resolve():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                shutil.rmtree(path)
        except FileNotFoundError:
            pass


def run_judge(submission_id: int) -> None:
    with SessionLocal() as db:
        claimed = db.execute(update(Submission).where(
            Submission.id == submission_id, Submission.status.in_(ACTIVE_STATUSES),
            Submission.lease_until < time.time(),
        ).values(status=SubmissionStatus.COMPILING, lease_until=time.time() + LEASE_SECONDS, compile_output=None))
        db.commit()
        if not claimed.rowcount:
            return
        submission = db.get(Submission, submission_id)
        try:
            problem = db.get(Problem, submission.problem_id)
            if problem is None or problem.data is None:
                raise ValueError("Missing test data")
            with zipfile.ZipFile(problem.data.zipfile) as archive:
                files = validate_archive(archive, problem.data.test_cases)
            answers = {case.output_file: files[case.output_file].decode("utf-8") for case in problem.data.test_cases}
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=f"{submission_id}-", dir=DATA_DIR) as directory:
                work_dir = Path(directory)
                work_dir.chmod(0o755)
                for name, content in files.items():
                    if name not in answers:
                        if name in {case.input_file for case in problem.data.test_cases}:
                            content = re.sub(rb'(?m)^(\s*load\s+"?(?:/app/)?source\.)hex(?="?\s*(?:\r?$))',
                                             rb'\1cod', content)
                        path = work_dir / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(content)
                        path.chmod(0o644)
                source_path = work_dir / "source.asm"
                source_path.write_text(prepare_source(submission.source), encoding="utf-8")
                source_path.chmod(0o644)
                deadline = time.monotonic() + TOTAL_TIMEOUT
                hex_path = _compile(db, submission, source_path, work_dir)
                _run_test_cases(db, submission, problem, hex_path, work_dir, answers, deadline)
        except _JudgeFailure:
            pass
        except Exception:
            logger.exception("Judge infrastructure/test-data failure for submission %s", submission_id)
            db.rollback()
            _finish(db, submission, SubmissionStatus.RUNTIME_ERROR)


def _bounded_capture(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    limit = 6 * 1024 * 1024
    output = bytearray()
    overflow = threading.Event()
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        def read_output():
            while chunk := process.stdout.read(65536):
                if len(output) + len(chunk) > limit:
                    overflow.set()
                    process.kill()
                    break
                output.extend(chunk)
        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            process.wait(timeout=timeout)
        except BaseException:
            process.kill()
            process.wait()
            raise
        finally:
            reader.join(timeout=5)
        if overflow.is_set():
            raise RuntimeError("Sandbox output limit exceeded")
        return subprocess.CompletedProcess(command, process.returncode, output.decode("utf-8", errors="replace"), "")


def _docker_run(work_dir: Path, command: list[str], timeout: float = COMPILE_TIMEOUT) -> subprocess.CompletedProcess:
    name = f"picjudge-{uuid.uuid4().hex}"
    args = [DOCKER_BIN, "run", "--name", name, "--rm", "--pull", "never",
            "--network", "none", "--memory", DOCKER_MEMORY, "--memory-swap", DOCKER_MEMORY,
            "--cpus", DOCKER_CPUS, "--pids-limit", DOCKER_PIDS_LIMIT,
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--read-only",
            "--user", "65534:65534", "--log-driver", "none",
            "--tmpfs", "/app:rw,noexec,nosuid,size=32m,mode=1777",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=8m,mode=1777",
            "-w", "/app"]
    volume = os.environ.get("JUDGE_DATA_VOLUME")
    if volume:
        subpath = work_dir.resolve().relative_to(DATA_DIR.resolve().parent).as_posix()
        args.extend(["--mount", f"type=volume,src={volume},dst=/input,volume-subpath={subpath},readonly"])
    else:
        args.extend(["-v", f"{work_dir.resolve()}:/input:ro"])
    args.extend([DOCKER_IMAGE, str(timeout), *command])
    try:
        try:
            result = _bounded_capture(args, timeout=timeout + 15)
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"Docker sandbox {name} did not finish within {timeout + 15}s") from exc
        if result.returncode:
            raise SandboxError(f"Docker sandbox could not execute: {result.stdout[:4000]}")
        payload = json.loads(result.stdout)
        if payload["returncode"] == 124:
            raise subprocess.TimeoutExpired(command, timeout)
        if command[0] == "gpasm" and payload["returncode"] == 0:
            for extension in ("hex", "cod"):
                artifact = work_dir / f"source.{extension}"
                artifact.write_bytes(base64.b64decode(payload[extension], validate=True))
                artifact.chmod(0o644)
        return subprocess.CompletedProcess(command, payload["returncode"], payload["stdout"], payload["stderr"])
    finally:
        try:
            cleanup = subprocess.run([DOCKER_BIN, "rm", "-f", name], capture_output=True, timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"Timed out cleaning sandbox {name}") from exc
        if cleanup.returncode and b"No such container" not in cleanup.stderr:
            raise SandboxError(f"Failed to clean sandbox {name}")


def _compile(db: Session, submission: Submission, source_path: Path, work_dir: Path) -> Path:
    submission.status = SubmissionStatus.COMPILING
    db.commit()
    try:
        result = _docker_run(work_dir, ["gpasm", "--mpasm-compatible", "-p", PIC_MODEL, source_path.name], COMPILE_TIMEOUT)
    except subprocess.TimeoutExpired:
        _finish(db, submission, SubmissionStatus.TIME_LIMIT_EXCEEDED)
        raise _JudgeFailure
    hex_path = source_path.with_suffix(".hex")
    if result.returncode != 0 or not hex_path.exists():
        submission.compile_output = compilation_feedback(result.stdout, result.stderr)
        _finish(db, submission, SubmissionStatus.COMPILE_ERROR)
        raise _JudgeFailure
    try:
        validate_cod(source_path.with_suffix(".cod").read_bytes())
    except (ValueError, OSError):
        submission.compile_output = 'Unsupported or invalid COD artifact. Embedded simulator directives (.direct/.sim/.command) are not allowed.'
        _finish(db, submission, SubmissionStatus.COMPILE_ERROR)
        raise _JudgeFailure
    return hex_path


def _run_test_cases(db: Session, submission: Submission, problem: Problem, hex_path: Path,
                   work_dir: Path, answers: dict[str, str], deadline: float) -> None:
    submission.status = SubmissionStatus.RUNNING
    db.commit()
    earned_points = 0
    max_cycles = None
    started_at = time.monotonic()
    for case in sorted(problem.data.test_cases, key=lambda item: item.id):
        try:
            remaining = deadline - time.monotonic() - 30
            if remaining <= 0:
                raise subprocess.TimeoutExpired("judge", TOTAL_TIMEOUT)
            output, cycles = _run_gpsim_case(case, hex_path, work_dir, min(problem.time_limit, remaining))
        except subprocess.TimeoutExpired:
            _finish(db, submission, SubmissionStatus.TIME_LIMIT_EXCEEDED)
            raise _JudgeFailure
        except subprocess.CalledProcessError:
            _finish(db, submission, SubmissionStatus.RUNTIME_ERROR)
            raise _JudgeFailure
        expected = _parse_key_values(answers[case.output_file])
        actual = _parse_key_values(output)
        if not expected:
            raise ValueError("Empty expected result")
        if any(actual.get(key) != value for key, value in expected.items()):
            _finish(db, submission, SubmissionStatus.WRONG_ANSWER)
            raise _JudgeFailure
        earned_points += case.points
        if cycles is not None:
            max_cycles = cycles if max_cycles is None else max(max_cycles, cycles)
    submission.time = time.monotonic() - started_at
    submission.cycles = max_cycles
    submission.points = float(earned_points)
    _update_best_score(db, submission.user_id, problem.id, earned_points)
    _finish(db, submission, SubmissionStatus.ACCEPTED)


def _run_gpsim_case(case: ProblemTestCase, hex_path: Path, work_dir: Path, time_limit: float) -> tuple[str, int | None]:
    result = _docker_run(work_dir, ["gpsim", "-i", "-p", PIC_MODEL, "-c", case.input_file], time_limit)
    result.check_returncode()
    if re.search(r"\*\*\*ERROR|ERROR:|No cpu has been selected|WDT expired reset|syntax error|No such file or directory|cannot open|failed to open", result.stdout + result.stderr, re.IGNORECASE):
        raise subprocess.CalledProcessError(1, result.args, result.stdout, result.stderr)
    return result.stdout, _extract_cycles(result.stdout)


def _parse_key_values(text: str) -> dict[str, str]:
    text = _strip_gpsim_prompts(text)
    result = parse_key_values(text)
    for line in text.splitlines():
        if re.fullmatch(r"\s*(?:[0-9a-fA-F]+\s+\w+\s*=\s*[0-9a-fA-F]+\s*)+", line):
            result.update(re.findall(r"[0-9a-fA-F]+\s+(\w+)\s*=\s*([0-9a-fA-F]+)", line))
        match = re.match(r"^\s*([0-9a-fA-F]{4}):\s+((?:[0-9a-fA-F]{2}\s+){15}[0-9a-fA-F]{2})(?:\s|$)", line)
        if match:
            base = int(match.group(1), 16)
            for offset, value in enumerate(match.group(2).split()):
                result[f"ram[0x{base + offset:03x}]"] = value.lower()
    return result
_CYCLES_RE = re.compile(r"^\s*(\d+)\s*=\s*0x[0-9A-Fa-f]+\s*$")


def _extract_cycles(output: str) -> int | None:
    for line in _strip_gpsim_prompts(output).splitlines():
        match = _CYCLES_RE.match(line)
        if match:
            return int(match.group(1))
    return None


def _strip_gpsim_prompts(text: str) -> str:
    return re.sub(r'(?m)^(?:\*\*gpsim>[ \t]*)+', '', text)


def _update_best_score(db: Session, user_id: int, problem_id: int, points: int) -> None:
    db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one()
    score = db.query(UserProblemScore).filter_by(user_id=user_id, problem_id=problem_id).first()
    if score is None:
        db.add(UserProblemScore(user_id=user_id, problem_id=problem_id, max_score=points))
    elif points > score.max_score:
        score.max_score = points


def _finish(db: Session, submission: Submission, status: SubmissionStatus) -> None:
    submission.status = status
    submission.lease_until = 0
    db.commit()
