"""對 serve_scan_events.py 找出的每個事件做**啟發式**檢查，輸出待人眼複查的清單。

> **2026-08-16 更正：這支的兩個檢查都比原本寫的弱，而且兩個都被實測推翻過。**
> 原本的說法是「客觀檢查」「拋球會被濾掉」，請不要再那樣讀。

兩個檢查各自的真實強度：

1. **腿有沒有在畫面內** — 用腳踝 visibility 與 y 座標判斷。**這會被騙**：畫面外的腿
   MediaPipe 會直接幻覺出來還回報高可見度。通過只代表「通過啟發式」，
   **不等於腿真的在畫面內**。所以 `legs-cut` 沒被標**不保證**樣本可用。

2. **是不是真的擊球** — 用正規化伸展（above_nose / torso）＋手肘接近伸直。
   **這擋不掉拋球**：拋球到頂點時手臂又高又直，`norm` 與 `elbow` 都會過關，甚至比
   真正的擊球更高更直。「實測拋球手肘 120-149 度」只是某一支片子的情形，不是通則。
   所以 `toss/prep` 沒被標**不保證**那一格是觸球。

   另外 `above_nose / torso` 在手部特寫上會爆掉（torso 塌到 clamp，比值到 5-7），
   要配 `serve_scan_events.py` 的 `MAX_NORM` 一起用。

**結論：這支只能用來排順序與縮小人眼要看的範圍，不能當品質保證。**
分割畫面、多人入鏡、比賽轉播、錯誤示範、靜態示範姿勢——機器一個都分不出來，
`usertut_serve_10` 就是通過了所有自動檢查、最後靠逐格看畫面才發現不是發球的。
詳見 Obsidian `30-decisions/2026-08-16-volleyform-reject-jump-serve-tutorial.md`。
"""

import cv2, json, os
from mediapipe import solutions

# --- 改這裡 -----------------------------------------------------------------
SRC = r"C:\path\to\your\serve_tutorial.mp4"
OUT = r"C:\path\to\output\dir"
MIN_NORM = 0.30       # 正規化伸展（above_nose / torso）
MIN_ELBOW = 160.0     # 擊球時手臂接近伸直
MIN_KNEE_VIS = 0.6
MIN_ANKLE_VIS = 0.5
MAX_ANKLE_Y = 0.99    # >=1.0 代表腳踝在畫面外
# ---------------------------------------------------------------------------


def main():
    events = json.load(open(os.path.join(OUT, "serve_events.json")))
    cap = cv2.VideoCapture(SRC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    results = []
    print(f"{'ev':>3} {'peak':>6} {'norm':>5} {'elbow':>6} {'knee_vis':>8} "
          f"{'ankle_vis':>9} {'ankleY':>7}  verdict")
    with solutions.pose.Pose(static_image_mode=True, model_complexity=1,
                             min_detection_confidence=0.5) as pose:
        for i, e in enumerate(events):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(e["peak_t"] * fps))
            ok, fr = cap.read()
            if not ok:
                continue
            res = pose.process(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            if not res.pose_landmarks:
                print(f"{i:3d} {e['peak_t']:6.1f}  NO POSE")
                continue
            lm = res.pose_landmarks.landmark
            knee_vis = min(lm[25].visibility, lm[26].visibility)
            ankle_vis = min(lm[27].visibility, lm[28].visibility)
            ankle_y = max(lm[27].y, lm[28].y)
            full = (knee_vis > MIN_KNEE_VIS and ankle_vis > MIN_ANKLE_VIS
                    and ankle_y < MAX_ANKLE_Y)
            strong = e["peak_norm"] >= MIN_NORM and e["peak_elbow"] >= MIN_ELBOW
            # 標籤是「啟發式的懷疑」不是判定：legs-vis 會被幻覺的腿騙過，
            # norm+elbow 擋不掉拋球。REVIEW 只代表「優先看」，不代表可用；
            # 帶問號的也一定要進 montage，不能自動濾掉。
            verdict = ("REVIEW" if (full and strong)
                       else "legs-cut?" if not full
                       else "low-reach?")
            print(f"{i:3d} {e['peak_t']:6.1f} {e['peak_norm']:5.2f} {e['peak_elbow']:6.0f} "
                  f"{knee_vis:8.2f} {ankle_vis:9.2f} {ankle_y:7.2f}  {verdict}")
            results.append({"i": i, "t": e["peak_t"], "norm": e["peak_norm"],
                            "elbow": e["peak_elbow"], "full": bool(full),
                            "strong": bool(strong), "verdict": verdict})
    cap.release()
    json.dump(results, open(os.path.join(OUT, "serve_verify.json"), "w"), indent=1)
    good = [r for r in results if r["verdict"] == "REVIEW"]
    print(f"\nREVIEW（仍需人眼看 montage）: {[r['i'] for r in good]}  n={len(good)}")
    print("標籤只是啟發式懷疑，不是判定：REVIEW 代表值得人眼看，不代表可用；")
    print("legs-cut? 會被幻覺的腿騙過，low-reach? 擋不掉拋球。全部都要人眼複查。")


if __name__ == "__main__":
    main()
