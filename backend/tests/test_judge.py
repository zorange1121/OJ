import subprocess
import zipfile
import os
import time
import pytest

from sqlalchemy.orm import sessionmaker

import services.judge as judge
from model import Problem, ProblemData, ProblemTestCase, Submission, User, UserProblemScore
from schemas.submissions import SubmissionStatus


def test_stale_cleanup_preserves_recent_active_and_unrelated_directories(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    _user, _problem, submission = _seed(db_session, tmp_path)
    submission.lease_until = time.time() + 600
    db_session.commit()
    root = tmp_path / 'work'
    root.mkdir()
    monkeypatch.setattr(judge, 'DATA_DIR', root)
    stale = root / '999-abcdefgh'
    active = root / f'{submission.id}-abcdefgh'
    recent = root / '998-abcdefgh'
    unrelated = root / 'keep-me'
    for path in (stale, active, recent, unrelated):
        path.mkdir()
        (path / 'source.asm').write_text('test')
        if path != recent:
            os.utime(path, (time.time() - 1300, time.time() - 1300))
    judge.cleanup_stale_workdirs()
    assert not stale.exists()
    assert active.exists() and recent.exists() and unrelated.exists()


@pytest.mark.parametrize('stdout,stderr', [('***ERROR: syntax error\nW = 05\n', ''), ('Exiting gpsim\n', '/app/missing.hex: No such file or directory\n')])
def test_simulator_zero_exit_does_not_hide_errors(tmp_path, monkeypatch, stdout, stderr):
    monkeypatch.setattr(judge, '_docker_run', lambda *args: subprocess.CompletedProcess('gpsim', 0, stdout, stderr))
    case = ProblemTestCase(input_file='1.in')
    with pytest.raises(subprocess.CalledProcessError):
        judge._run_gpsim_case(case, tmp_path / 'source.hex', tmp_path, 1)


def _make_zip(files: dict[str, str], path):
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def _seed(db_session, tmp_path):
    user = User(username="alice")
    problem = Problem(name="Add", description="", time_limit=1.0, points=100)
    db_session.add_all([user, problem])
    db_session.commit()

    zip_path = tmp_path / "data.zip"
    _make_zip({"1.in": "run\n", "1.out": "W = 3\n"}, zip_path)

    problem_data = ProblemData(problem_id=problem.id, zipfile=str(zip_path))
    db_session.add(problem_data)
    db_session.commit()

    db_session.add(
        ProblemTestCase(problem_data_id=problem_data.id, input_file="1.in", output_file="1.out", points=100)
    )
    db_session.commit()

    submission = Submission(user_id=user.id, problem_id=problem.id, source="MOVLW 0x01")
    db_session.add(submission)
    db_session.commit()

    return user, problem, submission


def _patch_session(monkeypatch, db_session):
    session_factory = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(judge, "SessionLocal", session_factory)


def test_run_judge_accepted(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")
    _user, _problem, submission = _seed(db_session, tmp_path)

    def fake_compile(db, submission, source_path, work_dir):
        hex_path = source_path.with_suffix(".hex")
        hex_path.touch()
        return hex_path

    monkeypatch.setattr(judge, "_compile", fake_compile)
    monkeypatch.setattr(judge, "_run_gpsim_case", lambda case, hex_path, work_dir, time_limit: ("W = 3\n", 42))

    judge.run_judge(submission.id)

    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.ACCEPTED
    assert submission.points == 100.0
    assert submission.cycles == 42

    score = (
        db_session.query(UserProblemScore)
        .filter(UserProblemScore.user_id == submission.user_id, UserProblemScore.problem_id == submission.problem_id)
        .first()
    )
    assert score is not None
    assert score.max_score == 100


def test_run_judge_compile_error(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")
    _user, _problem, submission = _seed(db_session, tmp_path)

    def fake_compile_fail(db, submission, source_path, work_dir):
        submission.status = SubmissionStatus.COMPILE_ERROR
        db.commit()
        raise judge._JudgeFailure

    monkeypatch.setattr(judge, "_compile", fake_compile_fail)

    judge.run_judge(submission.id)

    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.COMPILE_ERROR


def test_compile_failure_persists_only_safe_feedback(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, 'DATA_DIR', tmp_path / 'submissions')
    _user, _problem, submission = _seed(db_session, tmp_path)
    monkeypatch.setattr(judge, '_docker_run', lambda *args: subprocess.CompletedProcess('gpasm', 1,
        'source.asm:2:Error[181] Unknown opcode: "BAD"\n1.in:8:Error[113] hidden-input\n', ''))
    judge.run_judge(submission.id)
    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.COMPILE_ERROR
    assert 'source.asm:2:' in submission.compile_output
    assert 'BAD' in submission.compile_output and 'hidden-input' not in submission.compile_output


def test_run_judge_wrong_answer(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")
    _user, _problem, submission = _seed(db_session, tmp_path)

    def fake_compile(db, submission, source_path, work_dir):
        hex_path = source_path.with_suffix(".hex")
        hex_path.touch()
        return hex_path

    monkeypatch.setattr(judge, "_compile", fake_compile)
    monkeypatch.setattr(judge, "_run_gpsim_case", lambda case, hex_path, work_dir, time_limit: ("W = 4\n", 42))

    judge.run_judge(submission.id)

    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.WRONG_ANSWER
    assert (
        db_session.query(UserProblemScore)
        .filter(UserProblemScore.user_id == submission.user_id, UserProblemScore.problem_id == submission.problem_id)
        .first()
        is None
    )


def test_run_judge_time_limit_exceeded(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")
    _user, _problem, submission = _seed(db_session, tmp_path)

    def fake_compile(db, submission, source_path, work_dir):
        hex_path = source_path.with_suffix(".hex")
        hex_path.touch()
        return hex_path

    def fake_timeout(case, hex_path, work_dir, time_limit):
        raise subprocess.TimeoutExpired(cmd="gpsim", timeout=time_limit)

    monkeypatch.setattr(judge, "_compile", fake_compile)
    monkeypatch.setattr(judge, "_run_gpsim_case", fake_timeout)

    judge.run_judge(submission.id)

    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.TIME_LIMIT_EXCEEDED


@pytest.mark.parametrize("stage", ["compile", "simulate"])
def test_run_judge_docker_hang_is_not_tle(db_session, tmp_path, monkeypatch, stage):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")
    _user, _problem, submission = _seed(db_session, tmp_path)

    def hung_docker(*args, **kwargs):
        raise judge.SandboxError("docker hung")

    if stage == "compile":
        monkeypatch.setattr(judge, "_docker_run", hung_docker)
    else:
        def fake_compile(db, submission, source_path, work_dir):
            hex_path = source_path.with_suffix(".hex")
            hex_path.touch()
            return hex_path
        monkeypatch.setattr(judge, "_compile", fake_compile)
        monkeypatch.setattr(judge, "_run_gpsim_case", hung_docker)

    judge.run_judge(submission.id)

    db_session.refresh(submission)
    assert submission.status != SubmissionStatus.TIME_LIMIT_EXCEEDED
    assert submission.status == SubmissionStatus.RUNTIME_ERROR
    assert submission.lease_until == 0


def test_submission_records_created_at(db_session, tmp_path):
    _user, _problem, submission = _seed(db_session, tmp_path)
    db_session.refresh(submission)
    assert submission.created_at is not None


def test_extract_cycles_from_real_gpsim_output():
    real_output = """
**gpsim> cycles
100 = 0x00000064
**gpsim> quit
"""
    assert judge._extract_cycles(real_output) == 100


def test_extract_cycles_missing_returns_none():
    assert judge._extract_cycles("W = 05\npc = 0x64\n") is None


def test_parse_key_values_against_real_gpsim_output():
    real_output = """
**gpsim> **gpsim> SetProcessorByType FIXME
Extended linear address 0 0
Leaving pic_processor::LoadProgramFile
0x0000000000000063 p18f4520 0x00C6 0x3FFF INVALID
       00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f
0020:  05 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00    ................

ffffffff PC      = c8   fd8 status  = 00   fe8 W       = 05
fd8 status  = 00   fe8 W       = 05

W = 05
pc = 0x64
Exiting gpsim
"""
    values = judge._parse_key_values(real_output)
    assert {key: values[key] for key in ("PC", "status", "W", "pc")} == {
        "PC": "c8",
        "status": "00",
        "W": "05",
        "pc": "0x64",
    }
    assert values["ram[0x020]"] == "05"


def test_run_judge_no_test_data(db_session, tmp_path, monkeypatch):
    _patch_session(monkeypatch, db_session)
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")

    user = User(username="bob")
    problem = Problem(name="No Data", description="", time_limit=1.0, points=100)
    db_session.add_all([user, problem])
    db_session.commit()

    submission = Submission(user_id=user.id, problem_id=problem.id, source="MOVLW 0x01")
    db_session.add(submission)
    db_session.commit()

    judge.run_judge(submission.id)

    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.RUNTIME_ERROR
