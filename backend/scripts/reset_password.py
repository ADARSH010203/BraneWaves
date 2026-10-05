"""Reset password for adarsh@gmail.com to '1234567890'"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

async def main():
    import bcrypt
    from app.database import connect_db, get_db
    await connect_db()
    db = get_db()
    
    user = await db.users.find_one({"email": "adarsh@gmail.com"})
    if not user:
        print("User not found!")
        return
    
    print(f"Found user: {user['_id']} | name={user.get('name')} | email={user['email']}")
    
    new_password = "1234567890"
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": hashed}}
    )
    print(f"Password reset to '{new_password}' successfully!")

if __name__ == "__main__":
    asyncio.run(main())
