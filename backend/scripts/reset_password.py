"""Administrative password reset utility.

Usage:
    python scripts/reset_password.py --email user@example.com

The new password is read securely from the terminal and is never stored in
source code, command history, or logs.
"""
import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


async def reset_password(email: str) -> None:
    from app.database import connect_db, disconnect_db, get_db
    from app.security.password import hash_password

    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    await connect_db()
    try:
        db = get_db()
        user = await db.users.find_one({"email": email}, {"_id": 1})
        if not user:
            raise SystemExit("User not found.")

        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"hashed_password": hash_password(password), "provider": "local"}},
        )
        # Revoke every refresh session so existing sessions cannot survive reset.
        await db.sessions.delete_many({"user_id": user["_id"]})
        print("Password reset successfully; all refresh sessions were revoked.")
    finally:
        await disconnect_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a local user's password securely.")
    parser.add_argument("--email", required=True, help="Account email to reset")
    args = parser.parse_args()
    asyncio.run(reset_password(args.email))


if __name__ == "__main__":
    main()
