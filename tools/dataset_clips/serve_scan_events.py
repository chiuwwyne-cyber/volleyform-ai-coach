"""掃描發球教學長片，找出「過頭擊球」候選事件。

輸出 <OUT>/serve_events.json 與一張把關用 montage。

重要：伸展高度一律用 **above_nose / torso**（正規化）判斷，不能用畫面座標的
above_nose——遠景的人在畫面裡比較小，raw 值會系統性偏低，導致完整入鏡的好片被
誤判成「伸展不足」。詳見 tools/dataset_clips/README.md 與 Obsidian
30-decisions/2026-08-14-volleyform-tutorial-clip-montage-gate.md。

但正規化本身有個陷阱（2026-08-16 掃跳發球教學片時踩到）：**手部特寫**沒有軀幹，
`torso` 會塌到下限，`above_nose / torso` 就爆到 5～7，把最沒用的畫面排到最前面。
所以正規化一定要**配腿部可見度 gate 一起用**（MIN_LEG_VIS / MAX_ANKLE_Y），
沒有腿的畫面直接不進候選——反正 crouch 階段本來就需要腿。

同時記錄 **crouch 膝角**（擊球前 CROUCH_LOOKBACK 秒內的最低膝角）。判斷一支片子
是站姿還是跳發球全靠它，而這決定了片段能不能併進 `serve`：serve 目前的標準只描述
站姿發球，跳發球蹲到 90-105° 會被誤判，混進去則會把 band 拉成雙峰。
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
MIN_LEG_VIS = 0.5     # 膝＋踝可見度；擋掉手部特寫（否則 norm 會爆到 5～7）
MAX_ANKLE_Y = 0.99    # 腳踝低於畫面底端 = 腿被裁掉
# norm 的解剖學上界。整條手臂大約就是一個軀幹長，鼻子又在肩膀上方約 0.25 個軀幹，
# 所以手腕高過鼻子最多約 0.7 個軀幹（實測完整入鏡的發球是 0.5-0.95）。設 1.5 留了
# 一倍以上餘裕，只會擋掉「torso 塌掉」的畫面。**這道界線是必要的**：可見度 gate 擋
# 不住手部特寫——畫面外的腿 MediaPipe 會直接幻覺出來，還給高可見度。
MAX_NORM = 1.5
GAP = 0.6             # 事件之間的最大間隔（秒）
CROUCH_LOOKBACK = 1.6  # 秒；回頭在擊球前這段時間內找最低膝角
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
            kl, kr, al, ar = lm[25], lm[26], lm[27], lm[28]
            vis = min(sl.visibility, sr.visibility, max(wl.visibility, wr.visibility))
            leg_vis = min(kl.visibility, kr.visibility, al.visibility, ar.visibility)
            if wl.y < wr.y:
                up_w, up_s, up_e, side = wl, sl, el, "L"
            else:
                up_w, up_s, up_e, side = wr, sr, er, "R"
            elbow = ang(up_s, up_e, up_w)
            knee = min(ang(hl, kl, al), ang(hr, kr, ar))
            shoulder_y = (sl.y + sr.y) / 2
            hip_y = (hl.y + hr.y) / 2
            above_nose = nose.y - up_w.y          # 正值 = 手腕高過鼻子
            torso = max(0.05, hip_y - shoulder_y)  # 身體尺度
            rows.append({
                "t": round(t, 2), "ok": 1, "vis": round(vis, 2),
                "leg_vis": round(leg_vis, 2),
                "ankle_y": round(max(al.y, ar.y), 3),   # >1.0 = 腳踝掉出畫面
                "above_nose": round(above_nose, 4), "torso": round(torso, 3),
                "norm": round(above_nose / torso, 3),   # ← 判斷用這個
                "elbow": round(elbow, 1), "knee": round(knee, 1), "side": side,
            })
    cap.release()

    ok = [r for r in rows if r.get("ok")]
    print(f"samples={len(rows)} with_pose={len(ok)}")

    # 腿部 gate 要在 norm 之前擋掉：手部特寫的 torso 會塌，norm 會爆到 5～7，
    # 沒擋的話排序會把最沒用的畫面放第一個。
    framed = [r for r in ok if r["leg_vis"] > MIN_LEG_VIS and r["ankle_y"] < MAX_ANKLE_Y]
    print(f"whole body usably in frame={len(framed)}")

    cand = [r for r in framed
            if MIN_NORM < r["norm"] < MAX_NORM
            and r["elbow"] > MIN_ELBOW and r["vis"] > MIN_VIS]
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

    # 每個事件回頭找 crouch：擊球前 CROUCH_LOOKBACK 秒內、腿看得到的最低膝角。
    # 這是判斷「站姿發球 vs 跳發球」的依據，決定片段能不能併進 serve。
    by_t = {r["t"]: r for r in framed}
    times = sorted(by_t)
    for e in events:
        lo = e["peak_t"] - CROUCH_LOOKBACK
        window = [by_t[t] for t in times if lo <= t <= e["peak_t"]]
        e["crouch_knee"] = round(min((r["knee"] for r in window), default=float("nan")), 1)

    json.dump({"fps": fps, "rows": rows}, open(os.path.join(OUT, "serve_scan.json"), "w"), indent=1)
    json.dump(events, open(os.path.join(OUT, "serve_events.json"), "w"), indent=1)
    print(f"events={len(events)}")
    for i, e in enumerate(events):
        print(f"  #{i:2d} {e['start']:6.1f}-{e['end']:6.1f}s peak@{e['peak_t']:6.1f}s "
              f"norm={e['peak_norm']:.2f} elbow={e['peak_elbow']:.0f} "
              f"crouch_knee={e['crouch_knee']:.0f}")

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
        cv2.putText(fr, f"#{i} {e['peak_t']:.0f}s n{e['peak_norm']:.2f} "
                        f"e{e['peak_elbow']:.0f} k{e['crouch_knee']:.0f}",
                    (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 0), 1)
        r, c = divmod(i, cols)
        m[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = fr
    cap.release()
    cv2.imwrite(os.path.join(OUT, "serve_events.jpg"), m, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("saved serve_events.jpg  ← 人眼把關看這張")


if __name__ == "__main__":
    main()
