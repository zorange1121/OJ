
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from model import Problem, UserProblemScore
from services.auth import create_user

DEV_PASSWORD = "password123"


def main() -> None:
    if os.environ.get("APP_ENV") != "development":
        raise SystemExit("Demo seed is only allowed with APP_ENV=development; use scripts.create_admin for deployment")
    db = SessionLocal()
    try:
        alice = create_user(db, "alice", DEV_PASSWORD, is_admin=True)
        bob = create_user(db, "bob", DEV_PASSWORD, is_admin=False)

        led_blink = Problem(
            name="LED Blink",
            description="Toggle RB0 every 500ms using a busy-wait delay loop.",
            time_limit=2.0,
            points=100,
            user_count=0,
            ac_rate=0.0,
        )
        led_blink.authors.append(alice)

        add_two = Problem(
            name="Add Two Numbers",
            description="Read two bytes from PORTB, write their sum to PORTC.",
            time_limit=1.0,
            points=100,
            user_count=0,
            ac_rate=0.0,
        )
        add_two.authors.append(alice)

        db.add_all([led_blink, add_two])
        db.commit()

        db.add(UserProblemScore(user_id=alice.id, problem_id=led_blink.id, max_score=80))
        db.commit()

        print(f"Seeded users: {alice.id}={alice.username}, {bob.id}={bob.username} (password: {DEV_PASSWORD!r})")
        print(f"Seeded problems: {led_blink.id}={led_blink.name}, {add_two.id}={add_two.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
