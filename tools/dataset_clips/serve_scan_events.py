"""掃描發球教學長片，找出「過頭擊球」候選事件。

輸出 <OUT>/serve_events.json 與一張把關用 montage。

重要：伸展高度一律用 **above_nose / torso**（正規化）判斷，不能用畫面座標的
above_nose——遠景的人在畫面裡比較小，raw 值會系統性偏低，導致完整入鏡的好片被
誤判成「伸展不足」。詳見 tools/dataset_clips/README.md 與 Obsidian
30-decisions/2026-08-14-volleyform-tutorial-clip-montage-gate.md。
"""

import cv2, math, json, os, numpy as np
from mediapipe import solutions

# --- 改這裡 -----------------------------------------------------------------
SRC = r"C:\path\to\your\serve_tutorial.mp4"
OUT = r"C:\path\to\output\dir"
STRIDE = 3            # 每 N 影格取樣一次
MIN_NORM = 0.22       # 正規化伸展門檻（above_nose / torso）
MIN_ELBOW = 145.0     # 擊球時手臂應接近伸直；拋球/準備通常明顯彎曲
MIN_VIS = 0.5
GAP = 0.6             # 事件之間的最大間隔（秒）
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
                rows.append({"t": round(t, 2), "ok": 0})   # 通常是場景切換
                continue
            lm = res.pose_landmarks.landmark
            nose = lm[0]; wl, wr = lm[15], lm[16]; sl, sr = lm[11], lm[12]
            el, er = lm[13], lm[14]; hl, hr = lm[23], lm[24]
            vis = min(sl.visibility, sr.visibility, max(wl.visibility, wr.visibility))
            if wl.y < wr.y:
                up_w, up_s, up_e, side = wl, sl, el, "L"
            else:
                up_w, up_s, up_e, side = wr, sr, er, "R"
            elbow = ang(up_s, up_e, up_w)
            shoulder_y = (sl.y + sr.y) / 2
            hip_y = (hl.y + hr.y) / 2
            above_nose = nose.y - up_w.y          # 正值 = 手腕高過鼻子
            torso = max(0.05, hip_y - shoulder_y)  # 身體尺度
            rows.append({
                "t": round(t, 2), "ok": 1, "vis": round(vis, 2),
                "above_nose": round(above_nose, 4), "torso": round(torso, 3),
                "norm": round(above_nose / torso, 3),   # ← 判斷用這個
                "elbow": round(elbow, 1), "side": side,
            })
    cap.release()

    ok = [r for r in rows if r.get("ok")]
    print(f"samples={len(rows)} with_pose={len(ok)}")

    cand = [r for r in ok
            if r["norm"] > MIN_NORM and r["elbow"] > MIN_ELBOW and r["vis"] > MIN_VIS]
    print(f"candidate frames (normalized)={len(cand)}")

    events, cur = [], None
    for r in cand:
        if cur and r["t"] - cur["end"] <= GAP:
            cur["end"] = r["t"]
            if r["norm"] > cur["peak_norm"]:
                cur.update(peak_norm=r["norm"], peak_t=r["t"],
                           peak_elbow=r["elbow"], peak_above=r["above_nose"])
        else:
            if cur:
                events.append(cur)
            cur = {"start": r["t"], "end": r["t"], "peak_norm": r["norm"],
                   "peak_t": r["t"], "peak_elbow": r["elbow"],
                   "peak_above": r["above_nose"], "side": r["side"]}
    if cur:
        events.append(cur)

    json.dump({"fps": fps, "rows": rows}, open(os.path.join(OUT, "serve_scan.json"), "w"), indent=1)
    json.dump(events, open(os.path.join(OUT, "serve_events.json"), "w"), indent=1)
    print(f"events={len(events)}")
    for i, e in enumerate(events):
        print(f"  #{i:2d} {e['start']:6.1f}-{e['end']:6.1f}s peak@{e['peak_t']:6.1f}s "
              f"norm={e['peak_norm']:.2f} elbow={e['peak_elbow']:.0f}")

    # 場景切換（連續無 pose）——切片窗口不要跨過這些點
    gaps = [r["t"] for r in rows if not r.get("ok")]
    spans, g = [], None
    for t in gaps:
        if g and t - g[-1] <= 0.2:
            g.append(t)
        else:
            if g:
                spans.append((g[0], g[-1]))
            g = [t]
    if g:
        spans.append((g[0], g[-1]))
    json.dump(spans, open(os.path.join(OUT, "serve_cuts.json"), "w"), indent=1)
    print(f"scene cuts: {[(round(a,2), round(b,2)) for a, b in spans]}")

    # montage（每個事件的 peak 格）
    cap = cv2.VideoCapture(SRC)
    cols, cw, ch = 6, 210, 140
    rws = max(1, math.ceil(len(events) / cols))
    m = np.zeros((rws * ch, cols * cw, 3), dtype="uint8")
    for i, e in enumerate(events):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(e["peak_t"] * fps))
        okf, fr = cap.read()
        if not okf:
            continue
        fr = cv2.resize(fr, (cw, ch))
        cv2.rectangle(fr, (0, 0), (cw, 14), (0, 0, 0), -1)
        cv2.putText(fr, f"#{i} {e['peak_t']:.0f}s n{e['peak_norm']:.2f} e{e['peak_elbow']:.0f}",
                    (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 0), 1)
        r, c = divmod(i, cols)
        m[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = fr
    cap.release()
    cv2.imwrite(os.path.join(OUT, "serve_events.jpg"), m, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("saved serve_events.jpg  ← 人眼把關看這張")


if __name__ == "__main__":
    main()
