from model import Problem, User, UserProblemScore


def _seed_scores(db_session):
    alice = User(username="alice")
    bob = User(username="bob")
    problem = Problem(name="LED Blink", description="", time_limit=2.0, points=100)
    db_session.add_all([alice, bob, problem])
    db_session.commit()

    db_session.add(UserProblemScore(user_id=alice.id, problem_id=problem.id, max_score=80))
    db_session.commit()
    return alice, bob, problem


def test_get_user_progress(client, db_session):
    alice, _bob, problem = _seed_scores(db_session)

    resp = client.get(f"/api/users/{alice.id}/progress")

    assert resp.status_code == 200
    assert resp.json() == {
        "user_id": alice.id,
        "username": "alice",
        "total_score": 80.0,
        "problems": [
            {
                "problem_id": problem.id,
                "problem_name": "LED Blink",
                "points": 100.0,
                "max_score": 80.0,
            }
        ],
    }


def test_get_user_progress_not_found(client):
    resp = client.get("/api/users/999/progress")

    assert resp.status_code == 404


def test_leaderboard(client, db_session):
    alice, bob, _problem = _seed_scores(db_session)

    resp = client.get("/api/leaderboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0] == {"rank": 1, "user_id": alice.id, "username": "alice", "total_score": 80.0}
    assert body[1] == {"rank": 2, "user_id": bob.id, "username": "bob", "total_score": 0.0}
