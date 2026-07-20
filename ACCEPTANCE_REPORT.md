# VolleyForm AI Coach 驗收報告

日期：2026-07-20

## 結論

目前版本符合「一般使用者可用的排球動作 AI 教練 public beta」期待：可以用手機上傳或錄製影片、回放、即時分析、使用 3D 身體骨架與手部關節、顯示姿勢比對、提供修正建議與影片連結，並可透過 QR Code/PWA 在手機上使用。

它尚未達到完整商業團隊影片平台等級。進階缺口包含：語音註解、多機位同步、手動畫線標註、長期球員雲端資料庫與隊伍管理。

## 大眾運動 App 期待基準

參考公開運動分析工具的功能描述：

- Onform：錄影、分析、分享、慢動作與逐格檢視。
  https://onform.com/
- Kinovea：擷取、慢放、比較、標註、追蹤與量測動作。
  https://www.kinovea.org/
- CoachNow：AI 骨架追蹤、關節角度、左右比較、慢動作、註解。
  https://apps.apple.com/us/app/coachnow-sports-coaching-app/id596598472
- Hudl：錄影/上傳、快速找重點片段、個人化回饋、分享。
  https://www.hudl.com/products/hudl

## 功能驗收

| 項目 | 結果 | 證據 |
|---|---|---|
| 手機上傳照片/影片 | 通過 | `frontend/index.html` 的 `#video` 接受 `video/*,image/*` |
| 直接錄影與回放 | 通過 | `startRecordBtn`、`recordPreview.controls = true` |
| 即時分析 | 通過 | `startLiveBtn`、`startRealtimeAnalysis` |
| 手機省電 | 通過 | `mobile: frame_stride=4, process_width=480, max_frames=150` |
| 3D 身體與手部分析 | 通過 | `pose`、`hands` modality 與 `local-analyzer.js` |
| 姿勢比對 | 通過 | `poseCompareActual`、`poseCompareCorrected`、正面/側面切換 |
| 修正建議與影片 | 通過 | `coach_plan`、`video-link` |
| QR Code 分享 | 通過 | `shareQrBtn`、`runtime-share.json` |
| PWA 安裝/離線殼 | 通過 | `manifest.webmanifest`、`service-worker.js` |
| 語音註解 | 尚未支援 | 進階功能 |
| 多機位同步 | 尚未支援 | 進階功能 |
| 手動畫線標註 | 尚未支援 | 進階功能 |
| 長期雲端球員資料庫 | 尚未支援 | 進階功能 |

## 角度驗收

新增 `backend/angle_acceptance_test.py` 與 `backend/reference_convergence_test.py`，覆蓋三種角度情境與資料收斂檢查：

1. 職業/標準中位數角度：應通過，不產生問題。
2. 一般人些微誤差：落在 `accepted_range` 內，應通過。
3. 明顯錯誤角度：超出 `accepted_range`，應產生對應問題。

此測試會讀取最新的 `backend/reference_standards.json`，因此之後資料集再增加，測試會跟著最新標準更新。每個關節現在會輸出 `accepted_range`、`tolerance`、`convergence` 與 `convergence_state`，讓一般使用者正確但較不職業的角度可以被容許，同時資料越多會自然收斂。

## 角度標準狀態

| 動作 | 參考影片數 | 收斂狀態 |
|---|---:|---|
| 扣球 | 17 | contact stable，crouch usable |
| 發球 | 14 | stable |
| 攔網 | 6 | usable，仍需更多乾淨素材提升信心 |
| 接球 | 12 | usable |
| 舉球 | 6 | usable，仍需更多乾淨素材提升信心 |

## 驗收命令

```powershell
python backend\angle_acceptance_test.py
python backend\reference_convergence_test.py
python backend\user_expectation_test.py
python backend\phase_reference_test.py
python backend\self_test.py
python backend\backend_no_ui_test.py
python backend\feedback_contract_test.py
python backend\frontend_contract_test.py
python backend\frontend_quality_test.py
python backend\resource_contract_test.py
```
