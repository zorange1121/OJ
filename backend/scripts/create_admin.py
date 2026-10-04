import getpass
from database import SessionLocal
from services.auth import create_user
from schemas.auth import UserCreateRequest


def main():
    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password: ")
    if len(password) < 12:
        raise SystemExit("Use a password of at least 12 characters")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")
    data = UserCreateRequest(username=username, password=password, is_admin=True)
    with SessionLocal() as db:
        create_user(db, data.username, data.password, is_admin=True)
    print("Administrator created")


if __name__ == "__main__":
    main()
