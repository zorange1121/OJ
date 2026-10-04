from model import Problem


def _seed_problem(db_session):
    problem = Problem(name="LED Blink", description="", time_limit=2.0, points=100)
    db_session.add(problem)
    db_session.commit()
    return problem


def test_create_submission_requires_auth_header(client, db_session):
    problem = _seed_problem(db_session)

    resp = client.post("/api/submissions", json={"problem_id": problem.id, "source": "MOVLW 0x01"})

    assert resp.status_code == 401


def test_create_submission_rejects_invalid_token(client, db_session):
    problem = _seed_problem(db_session)

    resp = client.post(
        "/api/submissions",
        json={"problem_id": problem.id, "source": "MOVLW 0x01"},
        headers={"Authorization": "Bearer garbage"},
    )

    assert resp.status_code == 401


def test_create_and_get_submission(client, db_session, auth_headers):
    problem = _seed_problem(db_session)
    headers = auth_headers("alice")

    create_resp = client.post(
        "/api/submissions",
        json={"problem_id": problem.id, "source": "MOVLW 0x01"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "Pending"
    submission_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/submissions/{submission_id}", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["problem_id"] == problem.id
    assert body["source"] == "MOVLW 0x01"
    assert body["status"] == "RE"


def test_create_submission_unknown_problem(client, db_session, auth_headers):
    headers = auth_headers("alice")

    resp = client.post(
        "/api/submissions",
        json={"problem_id": 999, "source": "MOVLW 0x01"},
        headers=headers,
    )

    assert resp.status_code == 404


def test_get_submission_not_found(client, auth_headers):
    resp = client.get("/api/submissions/999", headers=auth_headers())

    assert resp.status_code == 404
