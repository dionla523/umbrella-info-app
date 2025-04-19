from app import app

# Vercel 將用此 WSGI 應用來處理所有請求
# Vercel Python Builder 要求導出名為 app 的 WSGI 變量
# 無需額外啟動程式碼，只需匯入 Flask app 即可
