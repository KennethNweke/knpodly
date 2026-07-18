#!/usr/bin/env python3
"""
One-time bootstrap script: creates the first admin user directly against the
database (bypasses the API, since there's no admin yet to call it).

Usage (from backend/ with the venv/deps available, or via
`docker compose exec backend python /app/../scripts/create-admin.py`):

    python scripts/create-admin.py --username admin --full-name "Admin User"

Prints a randomly generated password if --password is not supplied; the
user is expected to change it on first login via POST /api/v1/auth/change-password.
"""
import argparse
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.security import hash_password  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


async def main(username: str, full_name: str, password: str | None):
    generated = password is None
    password = password or secrets.token_urlsafe(12)

    async with AsyncSessionLocal() as db:
        db.add(User(username=username, full_name=full_name, password_hash=hash_password(password), role=UserRole.admin))
        await db.commit()

    print(f"Admin user '{username}' created.")
    if generated:
        print(f"Generated password: {password}")
        print("Store this securely and change it after first login.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.username, args.full_name, args.password))
