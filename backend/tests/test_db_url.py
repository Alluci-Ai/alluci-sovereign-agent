import os
from backend.config import settings
from backend.database import engine

print("ENV DATABASE_URL:", os.environ.get("DATABASE_URL"))
print("SETTINGS DATABASE_URL:", settings.DATABASE_URL)
print("ENGINE URL:", engine.url)
