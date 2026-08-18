"""掃攔網教學片,找「雙手過頭 + 腿在畫面內」的候選窗口。

## 為什麼要專門為 block 寫一支

`serve_scan_events.py` 的條件是「單手最高 + 手肘打直」,那是發球/扣球的形狀。
攔網不同:**雙手一起舉過頭、兩隻手臂都伸直**,而且判斷重點在起跳。

更關鍵的是取樣目的不同。2026-08-17 發現 block 的 crouch.knee 有 13/16 個樣本取自
「腳踝在畫面外、可見度 <0.5」的影格,清掉之後只剩 **6 個**樣本。所以這支掃描器的
第一優先不是「手舉得多高」,而是**腿到底看不看得見**——手的部分反正已經夠了,
補片補的是腿。

因此 `MIN_LEG_VIS` / `MAX_ANKLE_Y` 在這裡是**硬條件不是加分項**,而且刻意比
`serve_scan_events.py` 嚴(0.6 / 0.95),因為 `build_reference.py` 的可見度 gate
會在事後把不合格的膝角丟掉——與其切完才發現不能用,不如掃的時候就別選它。

## 這支**不會**告訴你的事

它找的是「姿勢像攔網」的影格,不是「這是攔網」。同一組肘/肩角度,單手伸手、
雙手跳舉、真的攔網幾乎沒有差別(見 SKILL.md 的說明)。多人畫面、插入的比賽轉播、
錯誤示範,機器一個都分不出來——**montage 人眼把關那關不能省**。
"""

import cv2, math, json, os, numpy as np
from mediapipe import solutions

# --- 改這裡 -----------------------------------------------------------------
SRC = r"C:\path\to\your\block_tutorial.mp4"
OUT = r"C:\path\to\output\dir"
STRIDE = 2
MIN_BOTH_ABOVE = 0.05   # 兩手腕都要高過鼻子這麼多(正規化到軀幹長)
MIN_ELBOW = 140.0       # 攔網雙臂接近伸直
MIN_VIS = 0.5
MIN_LEG_VIS = 0.6       # 硬條件:膝＋踝可見度。比 serve 嚴,理由見上面
MAX_ANKLE_Y = 0.95      # 硬條件:腳踝要明顯在畫面內,不是剛好卡邊
GAP = 0.7
CROUCH_LOOKBACK = 1.5
# ---------------------------------------------------------------------------

mp_pose = solutions.pose


def ang(a, b, c):
    v1 = (a.x - b.x, a.y - b.y); v2 = (c.x - b.x, c.y - b.y)
    d = math.hypot(*v1) * math.hypot(*v2)
    if d == 0:
        return 180.0
    return math.degrees(math.acos(max(-1, min(1, (v1[0]*v2[0] + v1[1]*v2[1]) / d))))


def main():
    cap = cv2.VideoCapture(SRC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    rows = []
    fi = 0
    with mp_pose.Pose(static_image_mode=False, model_complexity=1,
                      min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            fi += 1
            if fi % STRIDE != 0:
                continue
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); img.flags.writeable = False
            res = pose.process(img)
            t = fi / fps
            if not res.pose_landmarks:
                rows.append({"t": round(t, 2), "ok": 0})
                continue
            lm = res.pose_landmarks.landmark
            nose = lm[0]
            wl, wr, sl, sr, el, er = lm[15], lm[16], lm[11], lm[12], lm[13], lm[14]
            hl, hr, kl, kr, al, ar = lm[23], lm[24], lm[25], lm[26], lm[27], lm[28]
            vis = min(sl.visibility, sr.visibility)
            leg_vis = min(kl.visibility, kr.visibility, al.visibility, ar.visibility)
            torso = max(0.05, (hl.y + hr.y) / 2 - (sl.y + sr.y) / 2)
            # 攔網要**兩手**都過頭,取比較低的那隻當代表
            both_above = (nose.y - max(wl.y, wr.y)) / torso
            elbow_l, elbow_r = ang(sl, el, wl), ang(sr, er, wr)
            rows.append({
                "t": round(t, 2), "ok": 1, "vis": round(vis, 2),
                "leg_vis": round(leg_vis, 2),
                "ankle_y": round(max(al.y, ar.y), 3),
                "both_above": round(both_above, 3),
                "elbow_min": round(min(elbow_l, elbow_r), 1),
                "knee": round(min(ang(hl, kl, al), ang(hr, kr, ar)), 1),
                "hip_y": round((hl.y + hr.y) / 2, 3),
            })
    cap.release()

    ok = [r for r in rows if r.get("ok")]
    print(f"samples={len(rows)} with_pose={len(ok)}")
    framed = [r for r in ok if r["leg_vis"] > MIN_LEG_VIS and r["ankle_y"] < MAX_ANKLE_Y]
    print(f"legs usably in frame={len(framed)}  ({100*len(framed)/max(1,len(ok)):.0f}%)")

    cand = [r for r in framed
            if r["both_above"] > MIN_BOTH_ABOVE and r["elbow_min"] > MIN_ELBOW
            and r["vis"] > MIN_VIS]
    print(f"candidate frames={len(cand)}")

    events, cur = [], None
    for r in cand:
        if cur and r["t"] - cur["end"] <= GAP:
            cur["end"] = r["t"]
            if r["both_above"] > cur["peak"]:
                cur.update(peak=r["both_above"], peak_t=r["t"], peak_elbow=r["elbow_min"])
        else:
            if cur:
                events.append(cur)
            cur = {"start": r["t"], "end": r["t"], "peak": r["both_above"],
                   "peak_t": r["t"], "peak_elbow": r["elbow_min"]}
    if cur:
        events.append(cur)

    by_t = {r["t"]: r for r in framed}
    times = sorted(by_t)
    for e in events:
        window = [by_t[t] for t in times if e["peak_t"] - CROUCH_LOOKBACK <= t <= e["peak_t"]]
        e["crouch_knee"] = round(min((r["knee"] for r in window), default=float("nan")), 1)
        # 有沒有真的離地:髖部最低到擊球點之間上升多少(y 變小 = 往上)
        if window:
            e["hip_rise"] = round(max(r["hip_y"] for r in window) - by_t[e["peak_t"]]["hip_y"], 3)
        else:
            e["hip_rise"] = 0.0

    json.dump(rows, open(os.path.join(OUT, "block_scan.json"), "w"), indent=1)
    json.dump(events, open(os.path.join(OUT, "block_events.json"), "w"), indent=1)
    print(f"events={len(events)}\n")
    print(f"{'#':>3} {'window':>15} {'peak':>6} {'elbow':>6} {'crouch':>7} {'hip_rise':>9}")
    for i, e in enumerate(events):
        print(f"{i:3d} {e['start']:6.1f}-{e['end']:6.1f}s {e['peak']:6.2f} "
              f"{e['peak_elbow']:6.0f} {e['crouch_knee']:7.1f} {e['hip_rise']:9.3f}")

    cap = cv2.VideoCapture(SRC)
    cols, cw, ch = 6, 240, 160
    rws = max(1, math.ceil(len(events) / cols))
    m = np.zeros((rws * ch, cols * cw, 3), dtype="uint8")
    for i, e in enumerate(events):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(e["peak_t"] * fps))
        okf, fr = cap.read()
        if not okf:
            continue
        fr = cv2.resize(fr, (cw, ch))
        cv2.rectangle(fr, (0, 0), (cw, 15), (0, 0, 0), -1)
        cv2.putText(fr, f"#{i} {e['peak_t']:.0f}s k{e['crouch_knee']:.0f} r{e['hip_rise']:.2f}",
                    (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 1)
        r, c = divmod(i, cols)
        m[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = fr
    cap.release()
    cv2.imwrite(os.path.join(OUT, "block_events.jpg"), m, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("saved block_events.jpg  <- human gate")


if __name__ == "__main__":
    main()
