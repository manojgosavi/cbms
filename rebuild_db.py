"""
Quick script to rebuild the database from scratch after model changes.
Run this if you get "table already exists" or column-not-found errors.
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.models.database import get_session, engine, Base
from app.core.models.models import *

def rebuild():
    db_path = Path(__file__).parent / "data" / "cbms.db"
    
    # Back up old database
    if db_path.exists():
        backup_path = db_path.with_suffix('.db.backup')
        print(f"Backing up old database to {backup_path}...")
        import shutil
        shutil.copy(db_path, backup_path)
    
    # Drop all tables
    print("Dropping all existing tables...")
    Base.metadata.drop_all(engine)
    
    # Create all tables from scratch
    print("Creating new tables from models...")
    Base.metadata.create_all(engine)
    
    print("✅ Database rebuilt successfully!")
    print(f"   Database location: {db_path}")
    if db_path.with_suffix('.db.backup').exists():
        print(f"   Backup saved to: {db_path.with_suffix('.db.backup')}")

if __name__ == "__main__":
    try:
        rebuild()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
