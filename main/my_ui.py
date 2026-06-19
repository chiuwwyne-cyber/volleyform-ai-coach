import os
import textwrap
import webbrowser
from tkinter import Tk, filedialog

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import ctypes
except ImportError:
    ctypes = None

BASE_DIR = os.path.dirname(__file__)
WINDOW_SIZE = (1000, 700)

images = {
    "spike": cv2.imread(os.path.join(BASE_DIR, "spike.png")),
    "block": cv2.imread(os.path.join(BASE_DIR, "block.png")),
    "serve": cv2.imread(os.path.join(BASE_DIR, "serve.png")),
    "receive": cv2.imread(os.path.join(BASE_DIR, "receive.png")),
    "set": cv2.imread(os.path.join(BASE_DIR, "set.png")),
}

clicked_action = None
ui_command = None
active_screen = "menu"
link_regions = []
source_mode = "camera"
selected_video_path = None

buttons = {
    "spike": (70, 140, 310, 385),
    "block": (380, 140, 620, 385),
    "serve": (690, 140, 930, 385),
    "receive": (225, 420, 465, 665),
    "set": (535, 420, 775, 665),
    "exit": (810, 610, 950, 660),
}

source_buttons = {
    "camera_source": (650, 34, 765, 78),
    "video_source": (785, 34, 900, 78),
}

analysis_buttons = {
    "back": (704, 506, 816, 550),
    "playback": (832, 506, 944, 550),
    "report": (704, 566, 816, 610),
    "exit": (832, 566, 944, 610),
}

report_buttons = {
    "back": (704, 614, 782, 666),
    "exit": (888, 614, 966, 666),
}

playback_buttons = {
    "prev_frame": (704, 506, 816, 550),
    "toggle_play": (832, 506, 944, 550),
    "next_frame": (704, 566, 816, 610),
    "back": (832, 566, 944, 610),
}

label_map = {
    "spike": "扣球",
    "block": "攔網",
    "serve": "發球",
    "receive": "接球",
    "set": "托球",
    "exit": "離開",
}

action_name_map = {
    "spike": "扣球",
    "block": "攔網",
    "serve": "發球",
    "receive": "接球",
    "set": "托球",
}

ACTION_HINTS = {
    "spike": "3D 檢查肩肘伸展與落地膝角度",
    "block": "追蹤雙手高度、手肘伸直與膝蓋控制",
    "serve": "觀察肩肘出力鏈與下肢發力",
    "receive": "分析平台穩定與蹲姿角度",
    "set": "判斷手腕高度與托球手型",
}

ERROR_LABEL_MAP = {
    "elbow_not_straight": "手肘沒有完全伸直",
    "hands_not_high": "雙手高度不足",
    "knee_too_bent": "膝蓋彎曲/控制不足",
    "elbow_bad": "手肘角度不足",
    "knee_bad": "膝蓋角度不理想",
    "shoulder_low": "肩膀或擊球點偏低",
    "wrist_low": "手腕低於頭部",
    "elbow_position_bad": "托球手肘位置不穩",
    "setting_hands_not_detected": "托球手部未完整入鏡",
    "setting_fingers_closed": "托球手指張開不足",
    "setting_hand_spacing_bad": "托球雙手距離不理想",
    "setting_hands_unbalanced": "托球雙手高度不一致",
    "lobster_receive_risk": "吃蘿蔔風險偏高",
    "receive_platform_unbalanced": "接球平台左右不平",
    "receive_hands_apart": "接球雙手距離過開",
    "unknown_action": "無法判斷動作",
}

FONT_PATH = None
for fp in [
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/mingliu.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/arial.ttf",
]:
    if os.path.exists(fp):
        FONT_PATH = fp
        break

FONT_CACHE = {}


def get_font(font_size=24):
    if font_size not in FONT_CACHE:
        FONT_CACHE[font_size] = (
            ImageFont.truetype(FONT_PATH, font_size)
            if FONT_PATH
            else ImageFont.load_default()
        )
    return FONT_CACHE[font_size]


def draw_text(frame, text, position, font_size=24, color=(0, 0, 0)):
    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    rgb_color = (color[2], color[1], color[0])
    draw.text(position, str(text), font=get_font(font_size), fill=rgb_color)
    frame[:] = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def draw_wrapped_text(frame, text, x, y, max_chars=34, font_size=20, color=(0, 0, 0), line_gap=7):
    for line in textwrap.wrap(str(text), width=max_chars):
        draw_text(frame, line, (x, y), font_size, color)
        y += font_size + line_gap
    return y


def draw_limited_text(frame, text, x, y, max_chars=12, max_lines=2, font_size=17, color=(0, 0, 0), line_gap=5):
    lines = textwrap.wrap(str(text), width=max_chars)
    visible = lines[:max_lines]
    if len(lines) > max_lines and visible:
        visible[-1] = visible[-1].rstrip("，。,. ") + "..."

    for line in visible:
        draw_text(frame, line, (x, y), font_size, color)
        y += font_size + line_gap
    return y


def draw_panel(frame, rect, fill=(255, 255, 255), border=(220, 226, 232), thickness=1):
    x1, y1, x2, y2 = rect
    cv2.rectangle(frame, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), border, thickness)


def draw_button(frame, rect, label, fill=(34, 92, 185), color=(255, 255, 255)):
    x1, y1, x2, y2 = rect
    cv2.rectangle(frame, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (fill[0] - 15 if fill[0] > 15 else 0, fill[1], fill[2]), 1)
    text_x = x1 + max(10, ((x2 - x1) - len(label) * 24) // 2)
    draw_text(frame, label, (text_x, y1 + 15), 21, color)


def draw_image_cover(frame, img, rect):
    if img is None:
        return
    x1, y1, x2, y2 = rect
    target_w = x2 - x1
    target_h = y2 - y1
    ih, iw = img.shape[:2]
    scale = max(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = cv2.resize(img, (nw, nh))
    sx = max(0, (nw - target_w) // 2)
    sy = max(0, (nh - target_h) // 2)
    crop = resized[sy:sy + target_h, sx:sx + target_w]
    if crop.shape[1] != target_w or crop.shape[0] != target_h:
        crop = cv2.resize(crop, (target_w, target_h))
    frame[y1:y2, x1:x2] = crop


def draw_image_contain(frame, img, rect, background=(242, 239, 236)):
    if img is None:
        return
    x1, y1, x2, y2 = rect
    target_w = x2 - x1
    target_h = y2 - y1
    frame[y1:y2, x1:x2] = background

    ih, iw = img.shape[:2]
    scale = min(target_w / iw, target_h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = cv2.resize(img, (nw, nh))
    ox = x1 + (target_w - nw) // 2
    oy = y1 + (target_h - nh) // 2
    frame[oy:oy + nh, ox:ox + nw] = resized


def add_tint(frame, rect, color=(20, 42, 75), alpha=0.38):
    x1, y1, x2, y2 = rect
    overlay = np.full((y2 - y1, x2 - x1, 3), color, dtype=np.uint8)
    frame[y1:y2, x1:x2] = cv2.addWeighted(frame[y1:y2, x1:x2], 1 - alpha, overlay, alpha, 0)


def mouse_callback(event, x, y, flags, param):
    global clicked_action, ui_command, source_mode, selected_video_path

    if event == cv2.EVENT_MOUSEMOVE:
        set_arrow_cursor()
        return

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    if active_screen == "report":
        for x1, y1, x2, y2, url in link_regions:
            if x1 <= x <= x2 and y1 <= y <= y2:
                webbrowser.open(url)
                return

    if active_screen == "menu":
        for name, (x1, y1, x2, y2) in source_buttons.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if name == "camera_source":
                    source_mode = "camera"
                    selected_video_path = None
                else:
                    path = choose_video_file()
                    if path:
                        source_mode = "video"
                        selected_video_path = path
                return
        button_groups = (buttons,)
    elif active_screen == "report":
        button_groups = (report_buttons,)
    elif active_screen == "playback":
        button_groups = (playback_buttons,)
    else:
        button_groups = (analysis_buttons,)

    for button_group in button_groups:
        for name, (x1, y1, x2, y2) in button_group.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if name in action_name_map:
                    clicked_action = name
                    ui_command = None
                else:
                    ui_command = name
                return


def choose_video_file():
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="選擇排球動作影片",
        filetypes=[
            ("Video files", "*.mp4 *.mov *.avi *.mkv *.webm"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return path


def set_arrow_cursor():
    if ctypes is None or os.name != "nt":
        return
    user32 = ctypes.windll.user32
    arrow_cursor = user32.LoadCursorW(None, 32512)
    user32.SetCursor(arrow_cursor)


def make_canvas():
    frame = np.ones((WINDOW_SIZE[1], WINDOW_SIZE[0], 3), dtype=np.uint8)
    frame[:] = (242, 246, 248)
    width = WINDOW_SIZE[0]
    cv2.rectangle(frame, (0, 0), (width, 104), (36, 68, 112), -1)
    cv2.rectangle(frame, (0, 104), (width, 110), (244, 165, 63), -1)
    return frame


def draw_menu(frame):
    global active_screen
    active_screen = "menu"
    frame[:] = make_canvas()
    draw_text(frame, "排球 AI 3D 動作分析", (44, 24), 34, (255, 255, 255))
    draw_text(frame, "請用滑鼠選擇要分析的動作", (46, 64), 19, (215, 229, 242))

    for name in ["spike", "block", "serve", "receive", "set"]:
        rect = buttons[name]
        x1, y1, x2, y2 = rect
        draw_panel(frame, rect, (255, 255, 255), (210, 219, 228), 1)
        image_rect = (x1 + 10, y1 + 10, x2 - 10, y1 + 128)
        text_rect = (x1 + 14, y1 + 144, x2 - 14, y2 - 18)
        draw_image_contain(frame, images.get(name), image_rect)
        cv2.rectangle(frame, (image_rect[0], image_rect[1]), (image_rect[2], image_rect[3]), (230, 235, 240), 1)

        draw_text(frame, label_map[name], (text_rect[0], text_rect[1]), 27, (24, 38, 52))
        draw_limited_text(
            frame,
            ACTION_HINTS[name],
            text_rect[0],
            text_rect[1] + 46,
            max_chars=10,
            max_lines=2,
            font_size=16,
            color=(92, 103, 116),
            line_gap=5,
        )

    camera_color = (34, 92, 185) if source_mode == "camera" else (84, 102, 122)
    video_color = (34, 92, 185) if source_mode == "video" else (84, 102, 122)
    draw_button(frame, source_buttons["camera_source"], "攝影機", camera_color)
    draw_button(frame, source_buttons["video_source"], "選影片", video_color)

    if source_mode == "video" and selected_video_path:
        filename = os.path.basename(selected_video_path)
        draw_limited_text(frame, f"影片：{filename}", 46, 88, 30, 1, 14, (215, 229, 242), 4)
    else:
        draw_text(frame, "可用手機錄好影片，再選影片丟進來分析。", (46, 88), 14, (215, 229, 242))

    draw_button(frame, buttons["exit"], "離開", (220, 64, 64))


def draw_camera_panel(frame, camera_frame):
    panel = (28, 126, 646, 622)
    draw_panel(frame, panel, (255, 255, 255), (208, 218, 226), 1)
    if camera_frame is not None:
        draw_image_cover(frame, camera_frame, (42, 148, 632, 590))
    else:
        cv2.rectangle(frame, (42, 148), (632, 590), (28, 36, 45), -1)
        draw_text(frame, "等待攝影機畫面", (246, 350), 26, (230, 235, 240))
    draw_text(frame, "LIVE 3D POSE", (50, 602), 16, (80, 93, 108))


def draw_analysis_ui(frame, action, results, camera_frame=None):
    global active_screen
    active_screen = "analysis"
    frame[:] = make_canvas()
    draw_text(frame, "單視窗即時分析", (44, 24), 32, (255, 255, 255))
    draw_text(frame, f"目前動作：{action_name_map.get(action, action)}", (46, 64), 19, (215, 229, 242))

    draw_camera_panel(frame, camera_frame)

    info = (676, 126, 970, 622)
    draw_panel(frame, info, (255, 255, 255), (208, 218, 226), 1)
    draw_text(frame, "分析設定", (704, 160), 27, (24, 38, 52))
    draw_text(frame, f"動作：{action_name_map.get(action, action)}", (704, 210), 22, (70, 82, 96))
    draw_wrapped_text(
        frame,
        "請讓全身盡量入鏡，廣角鏡可保留手臂、膝蓋與落地動作的完整軌跡。",
        704,
        260,
        14,
        18,
        (92, 103, 116),
        7,
    )

    side = (28, 640, 970, 690)
    draw_panel(frame, side, (255, 255, 255), (208, 218, 226), 1)
    draw_text(frame, "偵測結果", (52, 653), 22, (24, 38, 52))

    ok = not results or results == ["good"] or results == ["ok"]
    status_text = "動作穩定" if ok else "需要修正"
    status_color = (28, 145, 83) if ok else (224, 90, 45)
    cv2.rectangle(frame, (175, 650), (330, 684), (235, 249, 242) if ok else (255, 240, 232), -1)
    draw_text(frame, status_text, (193, 656), 19, status_color)

    y = 654
    if ok:
        draw_wrapped_text(frame, "目前沒有偵測到明顯高風險姿勢。", 350, y, 18, 16, (70, 82, 96), 4)
    else:
        draw_text(frame, "需要注意：", (350, y), 16, (24, 38, 52))
        x = 440
        for result in results[:2]:
            if result in ["good", "ok"]:
                continue
            label = ERROR_LABEL_MAP.get(result, result)
            cv2.circle(frame, (x, y + 12), 4, (244, 165, 63), -1)
            draw_text(frame, label, (x + 12, y + 1), 14, (70, 82, 96))
            x += 170

    draw_button(frame, analysis_buttons["back"], "返回", (84, 102, 122))
    draw_button(frame, analysis_buttons["playback"], "回放", (34, 120, 135))
    draw_button(frame, analysis_buttons["report"], "報告", (34, 92, 185))
    draw_button(frame, analysis_buttons["exit"], "離開", (220, 64, 64))


def draw_report_window(report, action):
    global active_screen, link_regions
    link_regions = []
    active_screen = "report"
    frame = make_canvas()
    draw_text(frame, "智慧傷害風險與修正建議", (44, 24), 32, (255, 255, 255))
    draw_text(frame, f"動作：{action_name_map.get(action, action)}", (46, 64), 19, (215, 229, 242))

    y = 128
    if not report:
        draw_panel(frame, (40, 135, 960, 560), (255, 255, 255), (208, 218, 226), 1)
        draw_text(frame, "目前沒有可顯示的報告。", (70, 180), 24, (24, 38, 52))
    else:
        for idx, item in enumerate(report[:3], start=1):
            top = y
            bottom = min(y + 148, 590)
            draw_panel(frame, (40, top, 960, bottom), (255, 255, 255), (208, 218, 226), 1)
            priority = item.get("priority", "中")
            color = (224, 90, 45) if "高" in priority else (244, 143, 46)
            draw_text(frame, f"{idx}. {item.get('title', '動作建議')}", (66, y + 16), 23, (24, 38, 52))
            draw_text(frame, f"風險：{priority}", (816, y + 18), 20, color)
            y = draw_wrapped_text(frame, item.get("message", ""), 66, y + 52, 58, 18, (70, 82, 96), 5)

            fixes = item.get("fix_now", [])
            if fixes:
                y = draw_wrapped_text(frame, f"建議：{fixes[0]}", 66, y + 4, 58, 18, (22, 116, 76), 5)

            if item.get("video_keywords"):
                link_y = y + 4
                link_text = f"點擊觀看影片：{item['video_keywords']}"
                y = draw_wrapped_text(frame, link_text, 66, link_y, 62, 17, (160, 88, 18), 4)
                if item.get("video_url"):
                    link_regions.append((60, link_y - 4, 880, y + 2, item["video_url"]))
            y = bottom + 16
            if y > 590:
                break

    draw_text(frame, "完整影片連結會同步輸出在 VS Code Terminal。", (44, 628), 17, (82, 95, 108))
    draw_button(frame, report_buttons["back"], "返回", (84, 102, 122))
    draw_button(frame, report_buttons["exit"], "離開", (220, 64, 64))
    return frame


def draw_playback_ui(frame, action, results, playback_frame=None, index=0, total=0, playing=False):
    global active_screen
    active_screen = "playback"
    frame[:] = make_canvas()
    draw_text(frame, "動作回放分析", (44, 24), 32, (255, 255, 255))
    draw_text(frame, f"目前動作：{action_name_map.get(action, action)}", (46, 64), 19, (215, 229, 242))

    draw_camera_panel(frame, playback_frame)

    info = (676, 126, 970, 622)
    draw_panel(frame, info, (255, 255, 255), (208, 218, 226), 1)
    draw_text(frame, "回放控制", (704, 160), 27, (24, 38, 52))
    draw_text(frame, f"影格：{index + 1}/{max(total, 1)}", (704, 210), 22, (70, 82, 96))
    draw_wrapped_text(
        frame,
        "回放會同步顯示當下偵測到的姿勢問題，方便你對照自己的動作。",
        704,
        260,
        14,
        18,
        (92, 103, 116),
        7,
    )

    side = (28, 640, 970, 690)
    draw_panel(frame, side, (255, 255, 255), (208, 218, 226), 1)
    draw_text(frame, "此刻問題", (52, 653), 22, (24, 38, 52))

    ok = not results or results == ["good"] or results == ["ok"]
    if ok:
        draw_text(frame, "這一段沒有明顯高風險姿勢", (190, 656), 17, (28, 145, 83))
    else:
        x = 190
        for result in results[:3]:
            if result in ["good", "ok"]:
                continue
            label = ERROR_LABEL_MAP.get(result, result)
            cv2.circle(frame, (x, 668), 4, (244, 165, 63), -1)
            draw_text(frame, label, (x + 12, 657), 14, (70, 82, 96))
            x += 165

    draw_button(frame, playback_buttons["prev_frame"], "上一格", (84, 102, 122))
    draw_button(frame, playback_buttons["toggle_play"], "暫停" if playing else "播放", (34, 120, 135))
    draw_button(frame, playback_buttons["next_frame"], "下一格", (34, 92, 185))
    draw_button(frame, playback_buttons["back"], "返回", (220, 64, 64))
