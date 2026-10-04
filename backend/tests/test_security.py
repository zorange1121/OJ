import io
import json
import subprocess
import time
import zipfile

import jwt
import pika
import pytest
from sqlalchemy.orm import sessionmaker
from starlette.websockets import WebSocketDisconnect

from model import Problem, Submission
from schemas.problem import ProblemTestCaseIn
from schemas.submissions import SubmissionStatus
from services.errors import InvalidCredentialsError, InvalidTestDataError
from services.testdata import validate_archive
from services import auth, judge, queue
from settings import jwt_secret


def seed_submission(db, user):
    problem = Problem(name="Security", description="", time_limit=1, points=100)
    db.add(problem)
    db.flush()
    submission = Submission(user_id=user.id, problem_id=problem.id, source="secret answer",
                            status=SubmissionStatus.ACCEPTED)
    db.add(submission)
    db.commit()
    return submission


def test_submission_access(client, db_session, make_user):
    owner = make_user("owner")
    stranger = make_user("stranger")
    admin = make_user("admin", is_admin=True)
    submission = seed_submission(db_session, owner)
    submission.compile_output = 'source.asm:3: Error[181] Unknown opcode'
    db_session.commit()
    url = f"/api/submissions/{submission.id}"
    assert client.get(url).status_code == 401
    for user, status in [(owner, 200), (stranger, 403), (admin, 200)]:
        response = client.get(url, headers={"Authorization": f"Bearer {auth._create_access_token(user.id)}"})
        assert response.status_code == status
        if status != 200:
            assert "secret answer" not in response.text
            assert 'Unknown opcode' not in response.text
        else:
            assert response.json()['compile_output'] == submission.compile_output


def test_websocket_access(client, db_session, make_user, monkeypatch):
    import routers.ws as ws
    monkeypatch.setattr(ws, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    owner = make_user("owner")
    stranger = make_user("stranger")
    admin = make_user("admin", is_admin=True)
    submission = seed_submission(db_session, owner)
    submission.compile_output = 'source.asm:3: Error[181] Unknown opcode'
    db_session.commit()
    url = f"/api/submissions/{submission.id}/ws"
    for token, code in [("invalid", 4401), (auth._create_access_token(stranger.id), 4403)]:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f"{url}?token={token}"):
                pass
        assert error.value.code == code
    for user in (owner, admin):
        with client.websocket_connect(f"{url}?token={auth._create_access_token(user.id)}") as socket:
            payload = socket.receive_json()
            assert payload["status"] == "AC"
            assert payload['compile_output'] == submission.compile_output


@pytest.mark.parametrize("payload", [{"user_id": 1}, {"user_id": "1", "exp": 9999999999, "iat": 1},
                                     {"user_id": True, "exp": 9999999999, "iat": 1}])
def test_malformed_signed_token(payload):
    token = jwt.encode(payload, auth.JWT_SECRET, algorithm="HS256")
    with pytest.raises(InvalidCredentialsError):
        auth.decode_access_token(token)


@pytest.mark.parametrize("secret", ["", "short", "dev-insecure-secret-change-me-in-production-please"])
def test_production_rejects_weak_secret(monkeypatch, secret):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(RuntimeError):
        jwt_secret()


def test_large_and_multibyte_password_rejected(client):
    response = client.post("/api/auth/login", json={"username": "user", "password": "密" * 25})
    assert response.status_code == 422
    response = client.post("/api/auth/login", content=b"x" * (256 * 1024 + 1))
    assert response.status_code == 413


def test_login_rate_limit(client):
    for _ in range(10):
        assert client.post("/api/auth/login", json={"username": "missing", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "missing", "password": "wrong"}).status_code == 429


def validate_files(files, cases=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, value in files.items():
            entry = zipfile.ZipInfo()
            entry.filename = name
            entry.orig_filename = name
            archive.writestr(entry, value)
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as archive:
        return validate_archive(archive, cases if cases is not None else [
            ProblemTestCaseIn(input_file="1.in", output_file="1.out", points=100)])


@pytest.mark.parametrize("name", ["../outside", "/outside", "C:/outside", "a\\outside", "source.asm", "source.hex", "-script"])
def test_unsafe_archive_names(name):
    with pytest.raises(InvalidTestDataError):
        validate_files({"1.in": "quit", "1.out": "W = 05", name: "bad"})


def test_empty_cases_and_expected_output_rejected():
    with pytest.raises(InvalidTestDataError):
        validate_files({}, [])
    with pytest.raises(InvalidTestDataError):
        validate_files({"1.in": "quit", "1.out": "not an expected register value"})


def test_docker_timeout_cleans_container(monkeypatch, tmp_path):
    calls = []
    def timeout(args, timeout):
        calls.append(args)
        raise subprocess.TimeoutExpired(args, timeout)
    def cleanup(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, b"", b"")
    monkeypatch.setattr(judge, "_bounded_capture", timeout)
    monkeypatch.setattr(judge.subprocess, "run", cleanup)
    with pytest.raises(judge.SandboxError):
        judge._docker_run(tmp_path, ["gpsim", "-i"], 1)
    name = calls[0][calls[0].index("--name") + 1]
    assert calls[1] == [judge.DOCKER_BIN, "rm", "-f", name]
    assert "--read-only" in calls[0]
    assert "no-new-privileges" in calls[0]


def test_sandbox_runner_timeout_is_tle(monkeypatch, tmp_path):
    payload = '{"returncode": 124, "stdout": "", "stderr": ""}'
    monkeypatch.setattr(judge, "_bounded_capture", lambda args, timeout: subprocess.CompletedProcess(args, 0, payload, ""))
    monkeypatch.setattr(judge.subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(args, 0, b"", b""))
    with pytest.raises(subprocess.TimeoutExpired):
        judge._docker_run(tmp_path, ["gpsim", "-i"], 1)


def test_docker_cleanup_timeout_is_sandbox_error(monkeypatch, tmp_path):
    payload = '{"returncode": 0, "stdout": "W = 05", "stderr": ""}'
    def hung_cleanup(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])
    monkeypatch.setattr(judge, "_bounded_capture", lambda args, timeout: subprocess.CompletedProcess(args, 0, payload, ""))
    monkeypatch.setattr(judge.subprocess, "run", hung_cleanup)
    with pytest.raises(judge.SandboxError):
        judge._docker_run(tmp_path, ["gpsim", "-i"], 1)


def test_completed_and_leased_jobs_are_not_run(db_session, make_user, monkeypatch):
    submission = seed_submission(db_session, make_user("owner"))
    monkeypatch.setattr(judge, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    judge.run_judge(submission.id)
    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.ACCEPTED
    submission.status = SubmissionStatus.RUNNING
    submission.lease_until = time.time() + 60
    db_session.commit()
    judge.run_judge(submission.id)
    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.RUNNING


def test_expired_lease_recovers_to_terminal_state(db_session, make_user, monkeypatch):
    submission = seed_submission(db_session, make_user("owner"))
    submission.status = SubmissionStatus.RUNNING
    submission.lease_until = time.time() - 1
    db_session.commit()
    monkeypatch.setattr(judge, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    judge.run_judge(submission.id)
    db_session.refresh(submission)
    assert submission.status == SubmissionStatus.RUNTIME_ERROR
    assert submission.lease_until == 0


def test_broker_failure_preserves_pending_job(client, db_session, auth_headers, monkeypatch):
    headers = auth_headers()
    problem = Problem(name="P", description="", time_limit=1, points=100)
    db_session.add(problem)
    db_session.commit()
    def broken(_):
        raise pika.exceptions.AMQPConnectionError()
    monkeypatch.setattr(queue, "publish_submission", broken)
    response = client.post("/api/submissions", headers=headers, json={"problem_id": problem.id, "source": "END"})
    assert response.status_code == 200
    assert db_session.get(Submission, response.json()["id"]).status == SubmissionStatus.PENDING


def test_recovery_publishes_only_unleased_work(db_session, make_user, monkeypatch):
    import database
    submission = seed_submission(db_session, make_user("owner"))
    submission.status = SubmissionStatus.PENDING
    db_session.commit()
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(judge, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    published = []
    monkeypatch.setattr(queue, "publish_submission", published.append)
    queue.recover_submissions()
    assert published == [submission.id]
    submission.lease_until = time.time() + 60
    db_session.commit()
    published.clear()
    queue.recover_submissions()
    assert not published
