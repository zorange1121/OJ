from pathlib import Path
import secrets

path = Path(__file__).resolve().parent.parent / ".env"
with path.open("x", encoding="utf-8") as output:
    for key in ("JWT_SECRET", "POSTGRES_PASSWORD", "RABBITMQ_PASSWORD"):
        output.write(f"{key}={secrets.token_hex(32)}\n")
    output.write("FRONTEND_BIND=127.0.0.1\nFRONTEND_PORT=5173\nFRONTEND_ORIGIN=http://localhost:5173\n")
path.chmod(0o600)
print("Created .env with random secrets; keep this file private.")
