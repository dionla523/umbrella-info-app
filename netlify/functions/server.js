const { spawn } = require('child_process');
const path = require('path');

exports.handler = async function(event, context) {
  // 啟動 Flask 應用程式
  const flask = spawn('python', ['app.py'], {
    cwd: path.resolve(__dirname, '../..')
  });

  // 監聽 Flask 輸出
  flask.stdout.on('data', (data) => {
    console.log(`Flask stdout: ${data}`);
  });

  flask.stderr.on('data', (data) => {
    console.error(`Flask stderr: ${data}`);
  });

  // 等待 Flask 啟動
  await new Promise(resolve => setTimeout(resolve, 1000));

  // 轉發請求到 Flask
  const response = await fetch('http://localhost:5000' + event.path, {
    method: event.httpMethod,
    headers: event.headers,
    body: event.body
  });

  return {
    statusCode: response.status,
    body: await response.text(),
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'text/html'
    }
  };
};
