"""稽核：`_segment_overhead` 選中的 contact 格，有沒有第二個幾乎一樣高的候選？

## 為什麼要有這支

`serve`/`spike`/`block` 的 contact 取「**整段裡手腕最高的一格**」（全域最小 y）。
如果一段片子裡同時有拋球和擊球，而拋球那一刻手腕更高，band 就會被拿拋球姿勢校準。
2026-08-16 掃跳發球教學片時確認拋球到頂點確實可能比擊球還高，所以既有資料集也必須查。

## 這支能證明什麼、不能證明什麼

**能**：找出「有兩個高度接近的候選」的片段——那種情況下選誰是被雜訊決定的。

**不能**：證明選中的那一格真的是觸球。**只有一個峰的片子也可能整段都是拋球練習**，
那正是最初的失效模式。要確定只能逐格看畫面。所以「gap 大」只代表沒有第二個候選，
不代表已驗證正確。

## 一定要用平滑後的訊號

`_segment_overhead` 最小化的是 `_smooth()`（3 格移動平均）之後的序列，不是原始序列。
第一版稽核用原始序列算 gap，得到的「平手清單」**跟真實的完全不同**
（原始序列說 `pexels_6216964` 是 0.000 平手，平滑後其實是 0.0972，差很遠）。
同儕審查抓到這點。**要重現系統的行為就得用系統實際用的訊號。**

## 重現歷史結果

被隔離的片段會移到 `dataset/_rejected/`，所以預設只掃作用中的資料集，**跑不出當初
那張 27 段的表**。要重現請加 `--include-rejected`，它會把 `dataset/_rejected/` 裡
**檔名符合該動作**的片段一起掃進來。

用法：
```
.venv\\Scripts\\python.exe tools\\dataset_clips\\audit_contact_selection.py [action] [--include-rejected]
```
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from backend.phase_segmentation import _smooth, _wrist_y, segment_action  # noqa: E402
from pose.pose import get_pose_from_video  # noqa: E402

MAX_FRAMES = 300
MIN_SEPARATION = 8      # 第二候選至少離 contact 這麼多格，才算不同的「峰」
TIE_THRESHOLD = 0.01    # 平滑後高度差小於此，視為近乎平手


REJECTED_DIR = os.path.join("dataset", "_rejected")


def _clip_paths(action, include_rejected):
    """(顯示名稱, 路徑) 清單。加 include_rejected 才會帶入已隔離的片段。"""
    root = os.path.join("dataset", action)
    paths = [(name, os.path.join(root, name))
             for name in sorted(os.listdir(root)) if name.endswith(".mp4")]
    if include_rejected and os.path.isdir(REJECTED_DIR):
        # 隔離區五個動作共用，只認檔名對得上這個動作的。Pexels 檔名沒有動作前綴，
        # 所以只比對 usertut_<action>_*；要重現含 Pexels 的舊表得自己放回去。
        stem = "dig" if action == "receive" else action
        prefix = f"usertut_{stem}_"
        paths += [(name + " [rejected]", os.path.join(REJECTED_DIR, name))
                  for name in sorted(os.listdir(REJECTED_DIR))
                  if name.endswith(".mp4") and name.startswith(prefix)]
    return paths


def audit(action="serve", include_rejected=False):
    clips = _clip_paths(action, include_rejected)
    note = "  (含已隔離片段)" if include_rejected else ""
    print(f"{action}: {len(clips)} clips{note}  "
          f"(gap = 第二候選比 contact 低多少，平滑後；越小越可疑)\n")
    print(f"{'clip':30} {'n':>4} {'contact':>7} {'pos%':>5} {'2nd@':>5} {'gap':>8}")
    ties = []
    for name, path in clips:
        points = []
        for data in get_pose_from_video(path, process_width=640,
                                        frame_stride=2, include_image=False):
            points.append(data[0])
            if len(points) >= MAX_FRAMES:
                break
        if len(points) < 6:
            print(f"{name:30} SKIP (too few frames)")
            continue
        segments = segment_action(action, points)
        if not segments or "contact" not in segments:
            print(f"{name:30} SKIP (no contact phase)")
            continue
        contact = segments["contact"]
        smoothed = _smooth([_wrist_y(p) for p in points])
        far = [(smoothed[i], i) for i in range(len(smoothed))
               if abs(i - contact) >= MIN_SEPARATION]
        if not far:
            print(f"{name:30} {len(smoothed):4d} {contact:7d}  (clip too short to compare)")
            continue
        second, second_i = min(far)
        gap = second - smoothed[contact]
        mark = "  <- near tie" if gap < TIE_THRESHOLD else ""
        if mark:
            ties.append((name, round(gap, 4)))
        print(f"{name:30} {len(smoothed):4d} {contact:7d} "
              f"{contact / max(1, len(smoothed) - 1) * 100:4.0f}% {second_i:5d} {gap:8.4f}{mark}")

    print(f"\nnear ties (gap < {TIE_THRESHOLD}): {len(ties)}")
    for name, gap in ties:
        print(f"   {name}  gap={gap}")
    print("\n提醒：gap 大 ≠ 已驗證正確，只代表沒有第二個候選。要確認得看畫面。")


if __name__ == "__main__":
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    audit(positional[0] if positional else "serve",
          include_rejected="--include-rejected" in sys.argv)
