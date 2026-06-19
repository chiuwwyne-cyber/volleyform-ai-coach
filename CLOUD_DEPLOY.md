# Public Deployment

如果手機不在同一個 Wi-Fi，最穩的做法是把後端部署成公開 HTTPS 網址。這個專案已經支援兩種方式。

## 方式一：臨時公開網址

適合展示、測試、短時間使用。

```powershell
.\install_cloudflared.ps1
.\run_remote_tunnel.ps1
```

終端會印出 `https://*.trycloudflare.com`，手機直接開啟該網址即可。這個網址是臨時的，關掉 tunnel 後就會失效。

## 方式二：雲端主機

適合長期使用。專案已提供：

- `Dockerfile`
- `Procfile`
- `PORT` 環境變數支援

部署平台可以選 Render、Railway、Fly.io 或其他支援 Python/Docker 的服務。啟動指令：

```text
python backend/server.py --host 0.0.0.0
```

平台會透過 `PORT` 環境變數指定對外 port，後端會自動讀取。

部署完成後，手機直接開啟平台給你的 HTTPS 網址。若前端和 API 由同一個網址提供，「後端網址」保持空白即可。

## 注意

- 免費雲端主機第一次分析可能比較慢。
- MediaPipe 和 OpenCV 需要較多 CPU，建議選至少 1GB RAM 的環境。
- 手機使用時建議選「手機省電」模式，影片控制在 5 到 10 秒。
