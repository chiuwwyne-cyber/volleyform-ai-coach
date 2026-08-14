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
2. **伸展高度要除以軀幹長度**。直接用畫面座標比較，遠景的人會被系統性低估
   （`serve_scan_events.py` 有記 `torso`，用 `above_nose / torso` 排序）。
3. **腿要在畫面內**。`serve`/`spike`/`block` 會取蹲踞期的膝蓋，腿被切掉會產生垃圾資料。
   用腳踝 `visibility > 0.5` 且 `y < 0.99` 客觀判斷，不要目測縮圖。

## 已知限制

- 這些腳本是「當時可用」的狀態，路徑與接受清單寫死在檔案上方，沒有 CLI 參數。
- 來源教學影片**未** commit（體積與版權），所以無法完全重跑；`dataset/MANIFEST.md`
  記了每支片的來源與挑選理由，切好的 mp4 本身也在 `dataset/` 裡。
