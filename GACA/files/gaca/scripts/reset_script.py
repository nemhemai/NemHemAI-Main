import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import Base, engine
import app.models

print("Using database:", settings.database_url)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("[OK] Database reset - all tables dropped and recreated. Clean slate.")