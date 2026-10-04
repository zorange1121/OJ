import io
import json
import zipfile
import pytest

from model import Problem, User


def test_failed_problem_commit_removes_archive_and_rolls_back(db_session, tmp_path, monkeypatch):
    import services.problem as service
    from schemas import ProblemTestCaseIn
    admin = User(username='cleanup-admin', is_admin=True)
    db_session.add(admin)
    db_session.commit()
    monkeypatch.setattr(service, 'DATA_DIR', tmp_path)
    def fail_commit():
        raise RuntimeError('simulated storage failure')
    monkeypatch.setattr(db_session, 'commit', fail_commit)
    with pytest.raises(RuntimeError, match='storage failure'):
        service.create_problem(db_session, admin.id, 'test', '', 1, 100,
            [ProblemTestCaseIn(input_file='1.in', output_file='1.out', points=100)],
            _make_zip({'1.in': b'run\n', '1.out': b'W = 05\n'}))
    assert not list(tmp_path.iterdir())
    assert db_session.query(Problem).count() == 0


def _seed_problem(db_session):
    author = User(username="alice")
    problem = Problem(
        name="LED Blink",
        description="Blink an LED",
        time_limit=2.0,
        points=100,
        user_count=1,
        ac_rate=0.5,
    )
    problem.authors.append(author)
    db_session.add_all([author, problem])
    db_session.commit()
    return problem


def test_list_problems(client, db_session):
    problem = _seed_problem(db_session)

    resp = client.get("/api/problems")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": problem.id,
            "name": "LED Blink",
            "points": 100.0,
            "user_count": 1,
            "ac_rate": 0.5,
        }
    ]


def test_get_problem(client, db_session):
    problem = _seed_problem(db_session)

    resp = client.get(f"/api/problems/{problem.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "LED Blink"
    assert body["authors"] == [{"id": 1, "username": "alice"}]


def test_get_problem_not_found(client):
    resp = client.get("/api/problems/999")

    assert resp.status_code == 404


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buf.getvalue()


def test_create_problem_requires_admin(client, auth_headers):
    headers = auth_headers("alice", is_admin=False)

    resp = client.post(
        "/api/problems",
        data={
            "name": "LED Blink",
            "description": "desc",
            "time_limit": "2.0",
            "points": "100",
            "testcases": json.dumps([]),
        },
        files={"zipfile": ("data.zip", _make_zip({}), "application/zip")},
        headers=headers,
    )

    assert resp.status_code == 403


def test_create_problem_success(client, monkeypatch, tmp_path, auth_headers):
    import services.problem as problem_service

    monkeypatch.setattr(problem_service, "DATA_DIR", tmp_path)

    headers = auth_headers("admin", is_admin=True)

    zip_bytes = _make_zip({"1.in": b"1 2\n", "1.out": b"W = 03\n"})
    testcases = json.dumps([{"input_file": "1.in", "output_file": "1.out", "points": 100}])

    resp = client.post(
        "/api/problems",
        data={
            "name": "Add Two Numbers",
            "description": "desc",
            "time_limit": "1.0",
            "points": "100",
            "testcases": testcases,
        },
        files={"zipfile": ("data.zip", zip_bytes, "application/zip")},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Add Two Numbers"
    assert body["authors"] == [{"id": body["authors"][0]["id"], "username": "admin"}]
    assert (tmp_path / f"{body['id']}.zip").exists()


def test_create_problem_missing_testdata_file(client, auth_headers):
    headers = auth_headers("admin", is_admin=True)

    zip_bytes = _make_zip({"1.in": b"1 2\n"})
    testcases = json.dumps([{"input_file": "1.in", "output_file": "1.out", "points": 100}])

    resp = client.post(
        "/api/problems",
        data={
            "name": "Add Two Numbers",
            "description": "desc",
            "time_limit": "1.0",
            "points": "100",
            "testcases": testcases,
        },
        files={"zipfile": ("data.zip", zip_bytes, "application/zip")},
        headers=headers,
    )

    assert resp.status_code == 400
