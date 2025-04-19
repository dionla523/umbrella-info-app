from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
import csv
from io import StringIO, BytesIO
from pathlib import Path
from dotenv import load_dotenv
import base64

load_dotenv()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

try:
    from supabase import create_client, Client
    # Supabase 設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except ImportError:
    supabase = None

### 資料庫連線設定
# 優先使用環境變數 DATABASE_URL，若未設定或為 PostgreSQL（本地無 psycopg2），則回退到 SQLite
raw_db_url = os.getenv('DATABASE_URL', '')
if raw_db_url and raw_db_url.startswith('postgres'):
    # 本地開發 fallback to SQLite
    db_url = 'sqlite:///umbrella.db'
else:
    db_url = raw_db_url if raw_db_url else 'sqlite:///umbrella.db'
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
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
        try:
            # 獲取表單數據
            umbrella_type = request.form.getlist('umbrella_type')
            color = request.form.getlist('color')
            found_datetime = datetime.strptime(request.form.get('found_datetime'), '%Y-%m-%dT%H:%M')
            photo = request.files.get('photo')

            # 檢查必填欄位
            if not umbrella_type or not color or not found_datetime or not photo:
                flash('請填寫所有必填欄位')
                return redirect(url_for('form'))

            # 將多選框的值轉換為逗號分隔的字符串
            umbrella_type_str = ','.join(umbrella_type)
            color_str = ','.join(color)
            
            # 產生檔案名稱
            filename = secure_filename(datetime.now().strftime('%Y%m%d_%H%M%S_') + photo.filename)
            print(f"上傳的檔案名稱: {photo.filename}")
            print(f"生成的檔案名稱: {filename}")
            
            # 儲存照片到本地目錄
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"儲存路徑: {photo_path}")
            photo.save(photo_path)
            
            # 確認檔案是否存在
            if os.path.exists(photo_path):
                print(f"檔案已成功儲存")
            else:
                print(f"檔案儲存失敗")
                raise Exception("照片儲存失敗")
            
            # 儲存相對路徑到資料庫 (相對 static 資料夾)
            photo_path = f'uploads/{filename}'
            
            # 創建新的雨傘資訊記錄
            umbrella_info = UmbrellaInfo(
                umbrella_type=umbrella_type_str,
                color=color_str,
                found_datetime=found_datetime,
                photo_path=photo_path
            )
            
            # 保存到資料庫
            db.session.add(umbrella_info)
            db.session.commit()
            
            # 將資料寫入 CSV 檔案
            csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'csv', 'umbrella_records.csv')
            
            # 確保 CSV 目錄存在
            try:
                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                
                # 檢查檔案是否存在
                file_exists = os.path.exists(csv_path)
                
                # 寫入 CSV
                with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['id', 'umbrella_type', 'color', 'found_datetime', 'photo_path', 'created_at']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    # 如果檔案不存在，寫入標題列
                    if not file_exists:
                        writer.writeheader()
                    
                    # 寫入新的資料
                    writer.writerow({
                        'id': umbrella_info.id,
                        'umbrella_type': umbrella_info.umbrella_type,
                        'color': umbrella_info.color,
                        'found_datetime': umbrella_info.found_datetime.strftime('%Y-%m-%d %H:%M'),
                        'photo_path': umbrella_info.photo_path,
                        'created_at': umbrella_info.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    })
            except Exception as e:
                print(f"CSV 寫入失敗: {str(e)}")
                flash(f'CSV 寫入失敗: {str(e)}')
                return redirect(url_for('form'))
            
            return redirect('/thankyou.html')
            
        except Exception as e:
            print(f"發生錯誤: {str(e)}")
            flash(f'提交失敗: {str(e)}')
            return redirect(url_for('form'))
            
    # GET 分支: 查詢和篩選已上傳照片
    selected_type = request.args.get('umbrella_type', '')
    selected_color = request.args.get('color', '')
    selected_date = request.args.get('found_date', '')
    q = UmbrellaInfo.query
    all_records = UmbrellaInfo.query.all()
    types_set = set()
    colors_set = set()
    for u in all_records:
        for t in u.umbrella_type.split(','):
            types_set.add(t)
        for c in u.color.split(','):
            colors_set.add(c)
    if selected_type:
        q = q.filter(UmbrellaInfo.umbrella_type.contains(selected_type))
    if selected_color:
        q = q.filter(UmbrellaInfo.color.contains(selected_color))
    if selected_date:
        dt = datetime.strptime(selected_date, '%Y-%m-%d')
        q = q.filter(db.func.date(UmbrellaInfo.found_datetime) == dt.date())
    umbrellas = q.all()
    return render_template('form.html', umbrellas=umbrellas,
                           types=sorted(types_set), colors=sorted(colors_set),
                           selected_type=selected_type,
                           selected_color=selected_color,
                           selected_date=selected_date)

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

@app.route('/view_csv')
def view_csv():
    try:
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
        return output.getvalue()
    except Exception as e:
        return str(e), 500

@app.route('/view_csv.html')
def view_csv_html():
    try:
        # 從資料庫獲取所有記錄
        umbrellas = UmbrellaInfo.query.all()
        
        return render_template('view_csv.html', umbrellas=umbrellas)
    except Exception as e:
        flash(f'查看 CSV 失敗: {str(e)}')
        return redirect(url_for('form'))

@app.route('/thank-you')
def thank_you():
    return render_template('thankyou.html')

@app.route('/thank-you.html')
def thank_you_html():
    return render_template('thankyou.html')

@app.route('/thankyou.html')
def thankyou_html():
    return render_template('thankyou.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
