from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
import csv
from io import StringIO, BytesIO
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import base64

load_dotenv()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Supabase 設定
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 設定 PostgreSQL 資料庫
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

class UmbrellaInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    umbrella_type = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    found_datetime = db.Column(db.DateTime, nullable=False)
    photo_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        umbrella_type = request.form.get('umbrella_type')
        color = request.form.get('color')
        found_datetime = datetime.strptime(request.form.get('found_datetime'), '%Y-%m-%dT%H:%M')
        photo = request.files.get('photo')
        
        if photo:
            # 產生檔案名稱
            filename = secure_filename(datetime.now().strftime('%Y%m%d_%H%M%S_') + photo.filename)
            
            # 上傳照片到 Supabase Storage
            file_data = photo.read()
            result = supabase.storage.from_('umbrella-photos').upload(
                path=filename,
                file=file_data,
                file_options={"content-type": photo.content_type}
            )
            
            # 取得照片的公開 URL
            photo_path = supabase.storage.from_('umbrella-photos').get_public_url(filename)
        else:
            photo_path = None
            
        umbrella_info = UmbrellaInfo(umbrella_type=umbrella_type, color=color, found_datetime=found_datetime, photo_path=photo_path)
        db.session.add(umbrella_info)
        db.session.commit()

        # 將資料寫入 Supabase Storage 中的 CSV 檔案
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        
        # 寫入新的資料
        writer.writerow([
            umbrella_info.id,
            umbrella_info.umbrella_type,
            umbrella_info.color,
            umbrella_info.found_datetime.strftime('%Y-%m-%d %H:%M'),
            umbrella_info.photo_path,
            umbrella_info.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
        
        # 將 CSV 資料上傳到 Supabase Storage
        csv_content = csv_data.getvalue().encode('utf-8-sig')
        result = supabase.storage.from_('umbrella-csv').upload(
            path=f'records/{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            file=csv_content,
            file_options={"content-type": "text/csv"}
        )
        
        return redirect(url_for('thank_you'))
        
    return render_template('form.html')

@app.route('/export_csv')
def export_csv():
    # 從資料庫獲取所有記錄
    umbrellas = UmbrellaInfo.query.all()
    
    # 創建 CSV 檔案
    output = StringIO()
    output.write('\ufeff')  # 添加 BOM 標記以支援中文
    writer = csv.writer(output)
    
    # 寫入標題列
    writer.writerow(['ID', '雨傘類型', '顏色', '拾獲時間', '照片路徑', '建立時間'])
    
    # 寫入所有記錄
    for umbrella in umbrellas:
        writer.writerow([
            umbrella.id,
            umbrella.umbrella_type,
            umbrella.color,
            umbrella.found_datetime.strftime('%Y-%m-%d %H:%M'),
            umbrella.photo_path,
            umbrella.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # 準備回傳
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'umbrella_info_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app = app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
