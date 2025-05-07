import asyncio
import os
import sys

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import init_db
from app.settings import app_settings


async def test_db_connection():
    """Test that we can connect to the database."""
    try:
        await init_db(app_settings.DB_CONNECTION_STRING)
        print("Successfully connected to the database!")
        return True
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_db_connection())
    if success:
        print("Database connection test passed!")
    else:
        print("Database connection test failed!")
        sys.exit(1)
