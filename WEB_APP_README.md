# Volleyball AI Coach Web App

這個版本把後端分析和前端 UI 分開：後端只負責 API 與 MediaPipe 分析，前端負責錄影、上傳、回放與顯示教練建議。

## 同一台電腦使用

雙擊桌面上的「VolleyForm 啟動器」捷徑（或專案根目錄的 `VolleyForm.bat`），會自動啟動本機後端、嘗試建立公開 HTTPS 後端連線，並開啟開源前端：

```text
https://chiuwwyne-cyber.github.io/volleyform-ai-coach/
```

如果公開後端 tunnel 成功，啟動器會把後端網址放進前端的 `?backend=` 參數。這樣 QR Code 會指向公開前端網址，不會指向 `127.0.0.1`。

公開連線每次啟動都會產生新的網址，而且沒有密碼保護，記得只把網址分享給信任的人。

也可以手動執行：

```powershell
cd C:\Users\test\Desktop\volleyball
.\run_web_app.ps1
```

瀏覽器會開啟開源前端：

```text
https://chiuwwyne-cyber.github.io/volleyform-ai-coach/
```

`127.0.0.1:8000` 只作為電腦內部後端 API 與 tunnel origin，不作為 QR Code 網址。

## 手機和電腦同一個 Wi-Fi

先在電腦執行：

```powershell
.\run_web_app.ps1
```

網頁右上角有「產生 QR Code」按鈕，按下去會顯示公開前端網址的 QR code。若是由 `VolleyForm.bat` 啟動且 tunnel 成功，QR Code 會包含公開後端參數；若沒有 tunnel，手機仍可用前端本地 MediaPipe 分析。

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
3. 可以從手機相簿選照片或影片，也可以直接錄影。
4. 需要邊動邊看提示時，按「開啟即時分析」；停止後會立即釋放相機。
5. 錄影限制為 12 秒內，錄完可以先回放。
6. 按「開始分析」，等待 AI 顯示主要問題、優先修正建議與影片連結。

## 省資源設計

- 手機模式會降低處理寬度、跳幀與最大分析影格數。
- 即時分析會限制推論頻率，手機模式約每秒分析 3 幀。
- 頁面切到背景或停止即時分析時，會關閉相機並清除暫存骨架。
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

- `coach_summary`: 總結
- `coach_plan`: 優先修正方向與練習建議
- `primary_issues`: 主要問題、身體部位、立即提醒、影片建議
- `pose_compare`: 3D 姿勢比對用的關節資料（你的姿勢 vs. 正確姿勢示範動畫，正面/側面切換、關節顏色）
- `modalities`: 模組狀態
- `modality_results`: 各模組數值

## 測試

```powershell
.\.venv\Scripts\python.exe backend\self_test.py
```

```powershell
C:\Users\test\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe frontend\app_behavior_test.mjs
C:\Users\test\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe frontend\pose_geometry_test.mjs
```
