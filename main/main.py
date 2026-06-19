import os
import sys
from collections import deque

import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from action.block import check_block
from action.receive import check_receive
from action.serve import check_serve
from action.set import check_set
from action.spike import check_spike
from angle.angle import get_angles, get_hand_features, get_positions
from injury_database import ERROR_TO_INJURY, INJURY_DATABASE
import my_ui as ui
from pose.pose import get_pose, get_pose_from_video
from report_generator import format_report_text, generate_detection_report


def encode_replay_frame(frame, width=640, quality=70):
    if frame is None:
        return None
    h, w = frame.shape[:2]
    height = max(1, int(h * (width / w)))
    small = cv2.resize(frame, (width, height))
    ok, encoded = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return encoded if ok else None


def decode_replay_frame(encoded):
    if encoded is None:
        return None
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)


def check_action(action_type, angles, positions=None, hand_features=None):
    if action_type == "spike":
        return check_spike(angles)
    if action_type == "block":
        return check_block(angles)
    if action_type == "serve":
        return check_serve(angles)
    if action_type == "receive":
        return check_receive(angles, positions, hand_features)
    if action_type == "set":
        return check_set(angles, positions, hand_features)
    return ["unknown_action"]


def main():
    print("=== Volleyball AI 3D Analysis ===")

    mode = "menu"
    target_action = None
    history = deque(maxlen=3)
    pose_generator = None
    latest_report = []
    latest_camera_frame = None
    report_printed = False
    menu_cache = None
    last_results_key = None
    report_screen_cache = None
    replay_buffer = deque(maxlen=120)
    playback_index = 0
    playback_playing = False
    replay_sample_counter = 0

    window_name = "Volleyball AI 3D Analysis"
    width, height = ui.WINDOW_SIZE
    screen = np.ones((height, width, 3), dtype=np.uint8) * 255

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, width, height)
    cv2.setMouseCallback(window_name, ui.mouse_callback)

    try:
        while True:
            if ui.ui_command == "exit":
                break

            if mode == "menu":
                if menu_cache is None:
                    menu_cache = np.ones((height, width, 3), dtype=np.uint8) * 255
                    ui.draw_menu(menu_cache)
                screen[:] = menu_cache

                if ui.clicked_action is not None:
                    if ui.source_mode == "video" and not ui.selected_video_path:
                        ui.clicked_action = None
                        continue

                    target_action = ui.clicked_action
                    ui.clicked_action = None
                    ui.ui_command = None
                    history.clear()
                    latest_report = []
                    latest_camera_frame = None
                    report_printed = False
                    last_results_key = None
                    report_screen_cache = None
                    replay_buffer.clear()
                    playback_index = 0
                    playback_playing = False
                    replay_sample_counter = 0
                    if ui.source_mode == "video":
                        pose_generator = get_pose_from_video(
                            ui.selected_video_path,
                            process_width=720,
                            frame_stride=2,
                        )
                    else:
                        pose_generator = get_pose(
                            process_width=720,
                            frame_stride=1,
                        )
                    mode = "analysis"

            elif mode == "analysis":
                if pose_generator is None:
                    if ui.source_mode == "video" and ui.selected_video_path:
                        pose_generator = get_pose_from_video(
                            ui.selected_video_path,
                            process_width=720,
                            frame_stride=2,
                        )
                    else:
                        pose_generator = get_pose(
                            process_width=720,
                            frame_stride=1,
                        )

                try:
                    pose_data = next(pose_generator)
                    if len(pose_data) == 4:
                        landmarks, world_landmarks, camera_frame, hand_landmarks = pose_data
                    else:
                        landmarks, world_landmarks, camera_frame = pose_data
                        hand_landmarks = None
                    latest_camera_frame = camera_frame
                except StopIteration:
                    mode = "playback" if replay_buffer else "menu"
                    pose_generator = None
                    continue
                except Exception as e:
                    print("Camera/Pose error:", e)
                    mode = "menu"
                    pose_generator = None
                    continue

                angles = get_angles(landmarks, world_landmarks)
                positions = get_positions(landmarks, world_landmarks)
                hand_features = get_hand_features(hand_landmarks)

                if target_action == "set":
                    results = check_action(target_action, angles, positions, hand_features)
                elif target_action == "receive":
                    results = check_action(target_action, angles, positions, hand_features)
                else:
                    results = check_action(target_action, angles)

                if not isinstance(results, list):
                    results = ["unknown_action"]

                history.append(tuple(results))
                final_results = list(max(set(history), key=history.count)) if history else []
                results_key = tuple(final_results)
                if results_key != last_results_key:
                    latest_report = generate_detection_report(
                        final_results,
                        INJURY_DATABASE,
                        ERROR_TO_INJURY,
                    )
                    last_results_key = results_key

                replay_sample_counter += 1
                if replay_sample_counter % 2 == 0:
                    encoded_frame = encode_replay_frame(latest_camera_frame, width=480, quality=65)
                    if encoded_frame is not None:
                        replay_buffer.append((encoded_frame, tuple(final_results)))

                ui.draw_analysis_ui(screen, target_action, final_results, latest_camera_frame)

                if ui.ui_command == "report":
                    ui.ui_command = None
                    report_printed = False
                    report_screen_cache = ui.draw_report_window(latest_report, target_action)
                    mode = "report"
                elif ui.ui_command == "playback":
                    ui.ui_command = None
                    playback_index = max(0, len(replay_buffer) - 1)
                    playback_playing = False
                    mode = "playback"
                elif ui.ui_command == "back":
                    ui.ui_command = None
                    ui.clicked_action = None
                    target_action = None
                    pose_generator = None
                    history.clear()
                    latest_report = []
                    latest_camera_frame = None
                    last_results_key = None
                    report_screen_cache = None
                    replay_buffer.clear()
                    playback_index = 0
                    playback_playing = False
                    replay_sample_counter = 0
                    mode = "menu"

            elif mode == "report":
                if report_screen_cache is None:
                    report_screen_cache = ui.draw_report_window(latest_report, target_action)
                screen[:] = report_screen_cache
                if not report_printed:
                    print(
                        format_report_text(
                            latest_report,
                            ui.action_name_map.get(target_action, target_action),
                        )
                    )
                    report_printed = True

                if ui.ui_command == "back":
                    ui.ui_command = None
                    mode = "analysis"

            elif mode == "playback":
                if not replay_buffer:
                    ui.draw_playback_ui(screen, target_action, ["unknown_action"], None, 0, 0, False)
                else:
                    playback_index = max(0, min(playback_index, len(replay_buffer) - 1))
                    encoded_frame, replay_results = replay_buffer[playback_index]
                    replay_frame = decode_replay_frame(encoded_frame)
                    ui.draw_playback_ui(
                        screen,
                        target_action,
                        list(replay_results),
                        replay_frame,
                        playback_index,
                        len(replay_buffer),
                        playback_playing,
                    )

                    if playback_playing:
                        playback_index = (playback_index + 1) % len(replay_buffer)

                if ui.ui_command == "toggle_play":
                    ui.ui_command = None
                    playback_playing = not playback_playing
                elif ui.ui_command == "prev_frame":
                    ui.ui_command = None
                    playback_playing = False
                    playback_index = max(0, playback_index - 1)
                elif ui.ui_command == "next_frame":
                    ui.ui_command = None
                    playback_playing = False
                    if replay_buffer:
                        playback_index = min(len(replay_buffer) - 1, playback_index + 1)
                elif ui.ui_command == "back":
                    ui.ui_command = None
                    playback_playing = False
                    mode = "analysis"

            cv2.imshow(window_name, screen)
            wait_ms = 33 if mode == "playback" and playback_playing else 1
            key = cv2.waitKey(wait_ms) & 0xFF
            if key in (ord("q"), 27):
                break

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
