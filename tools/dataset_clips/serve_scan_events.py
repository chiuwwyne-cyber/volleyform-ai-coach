"""掃描發球教學長片，找出「過頭擊球」候選事件。

輸出 <OUT>/serve_events.json 與一張把關用 montage。

重要：伸展高度一律用 **above_nose / torso**（正規化）判斷，不能用畫面座標的
above_nose——遠景的人在畫面裡比較小，raw 值會系統性偏低，導致完整入鏡的好片被
誤判成「伸展不足」。詳見 tools/dataset_clips/README.md 與 Obsidian
30-decisions/2026-08-14-volleyform-tutorial-clip-montage-gate.md。

但正規化本身有個陷阱（2026-08-16 掃跳發球教學片時踩到）：**手部特寫**沒有軀幹，
`torso` 會塌到下限，`above_nose / torso` 就爆到 5～7。所以正規化要**配腿部 gate
一起用**（MIN_LEG_VIS / MAX_ANKLE_Y）再加上 MAX_NORM 上界。

注意 MIN_LEG_VIS 這道 gate **會被騙**：畫面外的腿 MediaPipe 會直接幻覺出來還回報高
可見度，所以通過它只代表「通過啟發式」，不等於全身真的完整入鏡。MAX_NORM 因此必要。

同時記錄 **crouch 膝角**（擊球前 CROUCH_LOOKBACK 秒內的最低膝角）。這只是**分流提示**，
不是判別器，也**不能拿去跟後端的 108.3° 比大小**——後端取的是「髖部最低那一格」的
`calculate_angle_3d` 3D 角、範圍是 contact 之前整段，這裡取的是「膝角最小那一格」的
影像平面 2D 角、固定回看 1.6 秒。三處都不同，而這些差異的誤差還沒量過，所以站姿
（約 110-150）與跳發（約 90-105）之間那 5° 的邊界不能只靠這個值判定。值偏低時要另外
確認（看畫面，或實際跑 build_reference 與評估流程）。

為什麼要在意站姿 vs 跳發：serve 目前的標準只描述站姿發球，而 `build_reference` 把同一
動作的所有片段**合成一條 band**（這點確定，code 就是這樣寫）。

**但「跳發球會被誤判」到目前為止還沒被量過**——常引的 90-105° 是掃描器的 2D 數字，
跟後端門檻 108.3° 不是同一個量。**如果**後端量出來的跳發球膝角確實明顯較低，混進去
就會被 IQR 剔掉（等於沒補）或把站姿共用的下限拉低（等於放寬門檻），那時才需要子型
感知的評估；**如果差距不大，這個顧慮可能根本不存在**。動手補素材之前先量一段。
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
# norm 上界。這**不是**解剖學硬上界：純比例推算是 0.7，但實測完整入鏡的發球到 0.95
# 就超過了（分母是影像投影的肩到髖距離，軀幹後仰或斜角取景會讓它縮短）。1.5 的理由是
# 兩個 regime 差一個數量級——正常 0.5-0.95、軀幹塌掉的特寫 5-7——它擋的是「分母失效」
# 這個故障模式。**這是硬過濾**：超標的影格在組 event 前就被丟掉，不會進 montage，
# 所以設太低會靜默丟掉好片且沒有任何提示。
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

    # 腿部 gate 先擋一輪：手部特寫的 torso 會塌，norm 會爆到 5～7。
    # 但這道 gate 擋不乾淨——畫面外的腿 MediaPipe 會幻覺出來還給高可見度——
    # 所以下面還要靠 MAX_NORM。通過這裡只代表「通過啟發式」，不是全身確實入鏡。
    framed = [r for r in ok if r["leg_vis"] > MIN_LEG_VIS and r["ankle_y"] < MAX_ANKLE_Y]
    print(f"passed leg-landmark heuristic (NOT verified full-body)={len(framed)}")

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
    # 分流提示而已，不是判別器——量法跟後端三處都不同（見檔案開頭），誤差未量測，
    # 不能直接對照 108.3°，也不足以單獨判定站姿 vs 跳發。
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
