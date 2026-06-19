# Volleyball AI Coach Web App

這個版本把後端分析和前端 UI 分開：後端只負責 API 與 MediaPipe 分析，前端負責錄影、上傳、回放與顯示教練建議。

## 同一台電腦使用

```powershell
cd C:\Users\test\Desktop\volleyball
.\run_web_app.ps1
```

瀏覽器開啟：

```text
http://127.0.0.1:8000
```

前端的「後端網址」可以留空，因為網頁和 API 在同一個網址。

## 手機和電腦同一個 Wi-Fi

先在電腦執行：

```powershell
.\run_web_app.ps1
```

再查電腦的區網 IP，例如 `192.168.1.23`。手機瀏覽器開啟：

```text
http://192.168.1.23:8000
```

前端的「後端網址」一樣可以留空。

## 手機不在同一個網路

不同網路時，手機不能直接連到你電腦的 `127.0.0.1` 或區網 IP。需要一個公開 HTTPS 入口，最簡單是 Cloudflare Tunnel、ngrok，或把後端部署到雲端主機。

第一次使用可以先下載專案本機版 `cloudflared`：

```powershell
.\install_cloudflared.ps1
```

下載完成後執行：

```powershell
.\run_remote_tunnel.ps1
```

終端會印出一個類似下面的公開網址：

```text
https://example.trycloudflare.com
```

手機直接打開這個公開網址。因為前端和後端都透過同一個公開網址提供服務，所以「後端網址」請留空。

如果你把後端部署在其他公開主機，也可以在前端「後端網址」填入：

```text
https://你的公開後端網址
```

再按「測試連線」。

長期使用可以部署到雲端主機。專案已提供 `Dockerfile`、`Procfile` 和 `PORT` 環境變數支援，細節請看 [CLOUD_DEPLOY.md](CLOUD_DEPLOY.md)。

## 使用流程

1. 選擇動作，例如扣球、攔網、發球、接球或舉球。
2. 手機建議選「手機省電」，可降低發熱與記憶體用量。
3. 可以上傳影片，也可以直接錄影。
4. 錄影限制為 12 秒內，錄完可以先回放。
5. 按「開始分析」，等待 AI 顯示分數、主要問題、修正建議與影片連結。

## 省資源設計

- 手機模式會降低處理寬度、跳幀與最大分析影格數。
- 前端錄影限制 12 秒，並限制解析度、幀率和 bitrate。
- 後端分析 API 只回傳關節資料與建議，不回傳每一張影像。
- 後端限制最大上傳大小，避免一次載入過大的影片。
- 時間軸只保留少量代表問題影格，方便手機顯示。

## API

健康檢查：

```text
GET /api/health
```

功能列表：

```text
GET /api/capabilities
```

影片分析：

```text
POST /api/analyze
Content-Type: multipart/form-data
```

欄位：

- `video`: 影片檔案
- `action`: `spike | block | serve | receive | set`
- `frame_stride`: 每幾幀分析一次
- `process_width`: 影像處理寬度
- `max_frames`: 最大分析影格數
- `modalities`: JSON，例如 `["pose","hands","ball"]`

回傳重點：

- `score`: 動作品質分數
- `coach_summary`: 總結
- `coach_plan`: 優先修正方向與練習建議
- `primary_issues`: 主要問題、身體部位、立即提醒、影片建議
- `timeline`: 代表影格問題分布
- `modalities`: 模組狀態
- `modality_results`: 各模組數值

## 測試

```powershell
.\.venv\Scripts\python.exe backend\self_test.py
```

```powershell
C:\Users\test\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe frontend\app_behavior_test.mjs
```
