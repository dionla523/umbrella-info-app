from app import app, db, UmbrellaInfo

with app.app_context():
    umbrellas = UmbrellaInfo.query.all()
    print("\n雨傘資訊記錄：")
    print("-" * 50)
    for umbrella in umbrellas:
        print(f"ID: {umbrella.id}")
        print(f"類型: {umbrella.umbrella_type}")
        print(f"顏色: {umbrella.color}")
        print(f"拾獲時間: {umbrella.found_datetime}")
        print(f"照片: {umbrella.photo_path}")
        print("-" * 50)
