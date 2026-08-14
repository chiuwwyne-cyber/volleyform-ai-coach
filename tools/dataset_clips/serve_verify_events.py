"""對 serve_scan_events.py 找出的每個事件做客觀檢查，輸出可採用清單。

兩個檢查（都不能用目測縮圖代替）：
1. **腿有沒有在畫面內** — serve/spike/block 會取蹲踞期的膝蓋，腿被切掉會產生垃圾
   資料。用腳踝 visibility 與 y 座標判斷，不是看縮圖。
2. **是不是真的擊球** — 用**正規化**伸展（above_nose / torso）＋手肘接近伸直。
   拋球／準備的格子手肘明顯彎曲（實測 120-149 度），會在這裡被濾掉。

輸出只是「客觀可採用」，**仍必須用 montage 人眼再看一次**：分割畫面、多人入鏡、
插入的比賽轉播畫面、錯誤示範，這些機器分不出來。
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
            verdict = ("CANDIDATE" if (full and strong)
                       else "legs-cut" if not full
                       else "toss/prep")
            print(f"{i:3d} {e['peak_t']:6.1f} {e['peak_norm']:5.2f} {e['peak_elbow']:6.0f} "
                  f"{knee_vis:8.2f} {ankle_vis:9.2f} {ankle_y:7.2f}  {verdict}")
            results.append({"i": i, "t": e["peak_t"], "norm": e["peak_norm"],
                            "elbow": e["peak_elbow"], "full": bool(full),
                            "strong": bool(strong), "verdict": verdict})
    cap.release()
    json.dump(results, open(os.path.join(OUT, "serve_verify.json"), "w"), indent=1)
    good = [r for r in results if r["verdict"] == "CANDIDATE"]
    print(f"\nCANDIDATE（仍需人眼看 montage）: {[r['i'] for r in good]}  n={len(good)}")
    print("legs-cut / toss-prep 已自動排除；分割畫面、多人、比賽轉播畫面要靠人眼。")


if __name__ == "__main__":
    main()
