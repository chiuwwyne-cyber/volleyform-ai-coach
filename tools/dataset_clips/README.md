# dataset_clips — 從教學長片挑出乾淨動作片段的工具

這些是 2026-08-14 擴充 `set`（14→24）與 `serve`（14→19）時實際用的腳本，原封保留下來
以便重用。它們**不是**自動化管線：中間一定要有一次人眼把關。

決策背景見 Obsidian `30-decisions/2026-08-14-volleyform-tutorial-clip-montage-gate.md`
與 `2026-08-04-volleyball-dataset-expansion-needs-human-labeling.md`。

## 流程

```
1. scan/locate  用 MediaPipe Pose 掃全片，找出候選窗口，輸出 JSON
2. montage      把每個候選的關鍵格拼成一張標註圖  ← 人眼在這裡把關
3. trim         只把人眼確認過的窗口用 cv2 切成 mp4，寫進 dataset/<action>/
4. build_reference.py 重算
5. 跑全套測試（11 後端 + 1 前端）——沒過就 git checkout 還原
```

每個腳本開頭都有常數（來源影片路徑、輸出路徑、接受清單、門檻），改那裡即可。
執行用專案的 venv：`.venv\Scripts\python.exe tools\dataset_clips\<script>.py`

## 檔案

| 檔案 | 用途 |
|---|---|
| `set_locate_windows.py` | 掃「雙手過頭且併攏」的舉球候選窗口 |
| `set_montage.py` | 舉球候選的把關圖 |
| `set_trim.py` | 切舉球片段（`ACCEPT` 清單在檔案上方） |
| `serve_scan_events.py` | 掃發球的過頭事件，記錄 elbow／above_nose／torso |
| `serve_verify_events.py` | 客觀檢查每個事件的**腳踝可見度**（腿有沒有入鏡） |
| `serve_montage.py` | 發球候選的把關圖（prep / contact / follow-through 三格） |
| `serve_trim.py` | 切發球片段（`WINDOWS` 清單在檔案上方） |

## 挑片時務必檢查的三件事

1. **關鍵瞬間要對得上系統的定義**。`serve`/`spike`/`block` 屬
   `phase_segmentation.OVERHEAD_ACTIONS`，contact 取「手腕最高的一格」。所以**下手發球
   不能混進 serve**——系統會把隨球動作當成擊球點。同理，沒有觸球的腳步練習片完全不能用。
   **拋球練習片同樣不能用，而且更危險**（2026-08-16 掃跳發球教學片時確認）：拋球到頂點
   時手臂又高又直，比真正擊球那一刻**還高還直**，contact 規則會直接選中它。混進去不是
   加雜訊，是把「擊球姿勢」教成拋球姿勢。
2. **伸展高度要除以軀幹長度，但一定要加上界**。直接用畫面座標比較，遠景的人會被系統性
   低估（所以要正規化）；然而手部特寫沒有軀幹，`torso` 會塌到 clamp，`above_nose / torso`
   反而爆到 5～7，**最沒用的畫面會排到第一名**。整條手臂約一個軀幹長、鼻子在肩上方約
   0.25 個軀幹，手腕高過鼻子最多約 0.7 個軀幹（實測完整入鏡的發球 0.5-0.95），所以
   `MAX_NORM = 1.5` 是解剖學上界不是調參。
3. **腿要在畫面內**。`serve`/`spike`/`block` 會取蹲踞期的膝蓋，腿被切掉會產生垃圾資料。
   用腳踝 `visibility > 0.5` 且 `y < 0.99` 客觀判斷，不要目測縮圖。
   **但可見度擋不住特寫**——畫面外的腿 MediaPipe 會直接幻覺出來還給高可見度，所以第 2 點
   的上界是必要的，兩道一起用才有效（該片候選 342 → 100）。
4. **切片前先看 crouch 膝角**。`serve_scan_events.py` 會回報擊球前 1.6 秒內的最低膝角：
   站姿發球約 110-150°、跳發球約 90-105°。目前 `serve` 的標準只描述站姿發球，兩者混在
   一起會把 band 拉成雙峰（分佈變寬但每一峰都不準），跟 2026-08-05 舉球那次的失敗同型。

## 已知限制

- 這些腳本是「當時可用」的狀態，路徑與接受清單寫死在檔案上方，沒有 CLI 參數。
- 來源教學影片**未** commit（體積與版權），所以無法完全重跑；`dataset/MANIFEST.md`
  記了每支片的來源與挑選理由，切好的 mp4 本身也在 `dataset/` 裡。
