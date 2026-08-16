"""產生發球候選的把關圖 —— **這一步是人眼把關，不能跳過**。

每個候選畫三格：準備（contact 前 0.6s）／擊球／隨球（+0.3s），這樣才看得出來
是不是完整的發球，而不是拋球、接球或剪接畫面。

預設看 serve_verify_events.py 標出的**全部**事件——包含被標為可疑的。把 PICK 設成 None 以外的
list 可以自己指定。

機器擋不掉、**只能靠人眼**的東西：分割畫面、多人同時入鏡、插入的比賽轉播畫面、
教學片裡的「錯誤示範」。看到這些就從 ACCEPT 清單剔除。
"""

import cv2, json, os, numpy as np

# --- 改這裡 -----------------------------------------------------------------
SRC = r"C:\path\to\your\serve_tutorial.mp4"
OUT = r"C:\path\to\output\dir"
PICK = None        # None = serve_verify.json 的全部事件；或自己給 [1, 2, 5]
# 刻意不過濾：serve_verify_events.py 的標籤只是啟發式懷疑，`legs-cut?` 會被幻覺的腿
# 騙過、`low-reach?` 擋不掉拋球，兩者都可能誤殺好片。人眼把關這一關要看得到全部，
# 被自動濾掉的東西人就永遠看不到了（2026-08-16 的教訓）。
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
        # 清單以 serve_events.json 為準（＝掃描找到的**全部**事件），verdict 只拿來
        # 排序。**不能反過來以 serve_verify.json 為準**：verifier 遇到讀不到影格或
        # 抓不到 pose 的事件會直接跳過，那些事件就永遠不會出現在把關圖裡——而讀不到
        # 影格、抓不到 pose 恰恰是最需要人看一眼的情況。
        rows = json.load(open(verify_path))
        verdicts = {r["i"]: r.get("verdict") for r in rows}
        order = {"REVIEW": 0, "low-reach?": 1, "legs-cut?": 2}
        # 沒被 verifier 涵蓋到的排最後，但一定在清單裡
        pick = sorted(range(len(events)),
                      key=lambda i: (order.get(verdicts.get(i), 3), i))
        missing = [i for i in pick if i not in verdicts]
        if missing:
            print(f"注意：verifier 沒涵蓋到的事件（讀不到影格／抓不到 pose）: {missing}"
                  f" —— 已保留在 montage 最後，請特別看這幾格")
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
