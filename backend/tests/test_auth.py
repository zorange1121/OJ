def test_login_success(client, make_user):
    make_user("alice", "secret123")

    resp = client.post("/api/auth/login", json={"username": "alice", "password": "secret123"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, make_user):
    make_user("alice", "secret123")

    resp = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})

    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})

    assert resp.status_code == 401


def test_protected_endpoint_rejects_missing_auth(client, make_user):
    problem_resp = client.get("/api/problems")
    assert problem_resp.status_code == 200

    resp = client.post("/api/submissions", json={"problem_id": 1, "source": "MOVLW 0x01"})
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.post(
        "/api/submissions",
        json={"problem_id": 1, "source": "MOVLW 0x01"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_create_user_requires_admin(client, auth_headers):
    headers = auth_headers("alice", is_admin=False)

    resp = client.post(
        "/api/users",
        json={"username": "charlie", "password": "pw"},
        headers=headers,
    )

    assert resp.status_code == 403


def test_admin_can_create_user(client, auth_headers):
    headers = auth_headers("admin", is_admin=True)

    resp = client.post(
        "/api/users",
        json={"username": "charlie", "password": "pw"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["username"] == "charlie"

    login_resp = client.post("/api/auth/login", json={"username": "charlie", "password": "pw"})
    assert login_resp.status_code == 200


def test_admin_create_user_rejects_duplicate_username(client, auth_headers):
    headers = auth_headers("admin", is_admin=True)
    client.post("/api/users", json={"username": "charlie", "password": "pw"}, headers=headers)

    resp = client.post("/api/users", json={"username": "charlie", "password": "pw2"}, headers=headers)

    assert resp.status_code == 409
