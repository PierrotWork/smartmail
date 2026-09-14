"""CLI: создать первого администратора.

Использование:
    python scripts/create_admin.py admin@example.com super-secret "Иван Админов"
"""

import sys
from pathlib import Path

# Позволяет запускать скрипт напрямую из папки scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.modules.auth.service import ensure_bootstrap_admin  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: create_admin.py <email> <password> [name]")
        return 2

    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Admin"

    with SessionLocal() as db:
        ensure_bootstrap_admin(db, email=email, password=password, name=name)

    print(f"OK: администратор {email} создан (или уже существовал).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
