"""
Seed the database with a test UmbrellaInfo record.
This script creates a record with umbrella_type="長柄", color="白色".
Run with: python seed_db.py
"""
from app import app, db, UmbrellaInfo
from datetime import datetime

with app.app_context():
    # Create test record
    test = UmbrellaInfo(
        umbrella_type="長柄",
        color="白色",
        found_datetime=datetime.now(),
        photo_path="uploads/test.jpg"
    )
    db.session.add(test)
    db.session.commit()
    print(f"已插入測試記錄，ID={test.id}")
