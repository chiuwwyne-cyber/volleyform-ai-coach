"""產生發球候選的把關圖 —— **這一步是人眼把關，不能跳過**。

每個候選畫三格：準備（contact 前 0.6s）／擊球／隨球（+0.3s），這樣才看得出來
是不是完整的發球，而不是拋球、接球或剪接畫面。

預設看 serve_verify_events.py 判定為 CANDIDATE 的事件；把 PICK 設成 None 以外的
list 可以自己指定。

機器擋不掉、**只能靠人眼**的東西：分割畫面、多人同時入鏡、插入的比賽轉播畫面、
教學片裡的「錯誤示範」。看到這些就從 ACCEPT 清單剔除。
"""

import cv2, json, os, numpy as np

# --- 改這裡 -----------------------------------------------------------------
SRC = r"C:\path\to\your\serve_tutorial.mp4"
OUT = r"C:\path\to\output\dir"
PICK = None        # None = 用 serve_verify.json 的 CANDIDATE；或自己給 [1, 2, 5]
LEAD = -0.6        # 準備格（相對 peak 的秒數）
TRAIL = 0.3        # 隨球格
# ---------------------------------------------------------------------------


def main():
    events = json.load(open(os.path.join(OUT, "serve_events.json")))

    pick = PICK
    if pick is None:
        verify_path = os.path.join(OUT, "serve_verify.json")
        if not os.path.exists(verify_path):
            raise SystemExit(
                "找不到 serve_verify.json —— 請先跑 serve_verify_events.py，"
                "或直接在本檔設定 PICK=[...]"
            )
        pick = [r["i"] for r in json.load(open(verify_path)) if r.get("verdict") == "CANDIDATE"]
    if not pick:
        raise SystemExit("沒有候選事件可看（PICK 為空）")
    print(f"montage 事件: {pick}")

    cap = cv2.VideoCapture(SRC)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    cols, cw, ch = 3, 320, 200
    m = np.zeros((len(pick) * ch, cols * cw, 3), dtype="uint8")
    for r, idx in enumerate(pick):
        e = events[idx]
        for c, dt in enumerate((LEAD, 0.0, TRAIL)):
            t = max(0, e["peak_t"] + dt)
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, fr = cap.read()
            if not ok:
                continue
            fr = cv2.resize(fr, (cw, ch))
            label = {LEAD: "prep", 0.0: "CONTACT", TRAIL: "follow"}[dt]
            cv2.rectangle(fr, (0, 0), (cw, 16), (0, 0, 0), -1)
            cv2.putText(fr, f"#{idx} {t:.1f}s {label} n{e['peak_norm']:.2f}",
                        (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 0), 1)
            m[r*ch:(r+1)*ch, c*cw:(c+1)*cw] = fr
    cap.release()
    p = os.path.join(OUT, "serve_montage.jpg")
    cv2.imwrite(p, m, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"saved {p}")
    print("看過後，把要保留的窗口填進 serve_trim.py 的 WINDOWS（避開 serve_cuts.json 的場景切換點）")


if __name__ == "__main__":
    main()
