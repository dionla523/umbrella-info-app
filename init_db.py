import os
os.environ['DATABASE_URL'] = ''
from app import app, db

with app.app_context():
    db.drop_all()  # 刪除所有表格
    db.create_all()  # 重新創建表格
    print("資料庫已重新初始化")
