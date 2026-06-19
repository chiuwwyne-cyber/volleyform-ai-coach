import cv2
from mediapipe import solutions

mp_pose = solutions.pose
mp_holistic = solutions.holistic
mp_hands = solutions.hands
mp_drawing = solutions.drawing_utils
mp_styles = solutions.drawing_styles


def _configure_wide_camera(cap, width=1280, height=720, fps=30):
    """Ask the camera for a wide 16:9 frame so full-body motion stays visible."""
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def _resize_for_processing(frame, process_width):
    if process_width is None:
        return frame

    h, w = frame.shape[:2]
    if w <= process_width:
        return frame

    process_height = max(1, int(h * (process_width / w)))
    return cv2.resize(frame, (process_width, process_height), interpolation=cv2.INTER_AREA)


def _draw_holistic_landmarks(image, results):
    mp_drawing.draw_landmarks(
        image,
        results.pose_landmarks,
        mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style(),
    )

    if results.left_hand_landmarks:
        mp_drawing.draw_landmarks(
            image,
            results.left_hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            landmark_drawing_spec=mp_styles.get_default_hand_landmarks_style(),
            connection_drawing_spec=mp_styles.get_default_hand_connections_style(),
        )

    if results.right_hand_landmarks:
        mp_drawing.draw_landmarks(
            image,
            results.right_hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            landmark_drawing_spec=mp_styles.get_default_hand_landmarks_style(),
            connection_drawing_spec=mp_styles.get_default_hand_connections_style(),
        )


def _pose_stream(
    cap,
    process_width=720,
    frame_stride=1,
    draw_landmarks=True,
    include_image=True,
):
    frame_index = 0

    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        refine_face_landmarks=False,
        min_detection_confidence=0.45,
        min_tracking_confidence=0.45,
    ) as holistic:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_index += 1
            if frame_stride > 1 and frame_index % frame_stride != 0:
                continue

            image = _resize_for_processing(frame, process_width)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = holistic.process(image)

            output_image = None
            if include_image:
                image.flags.writeable = True
                output_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks:
                if include_image and draw_landmarks:
                    _draw_holistic_landmarks(output_image, results)

                image_landmarks = results.pose_landmarks.landmark
                world_landmarks = (
                    results.pose_world_landmarks.landmark
                    if results.pose_world_landmarks
                    else None
                )
                hand_landmarks = {
                    "left": results.left_hand_landmarks.landmark
                    if results.left_hand_landmarks
                    else None,
                    "right": results.right_hand_landmarks.landmark
                    if results.right_hand_landmarks
                    else None,
                }
                yield image_landmarks, world_landmarks, output_image, hand_landmarks


def get_pose(camera_index=0, process_width=720, frame_stride=1):
    cap = cv2.VideoCapture(camera_index)
    _configure_wide_camera(cap)

    if not cap.isOpened():
        print("Cannot open camera.")
        return

    try:
        yield from _pose_stream(
            cap,
            process_width=process_width,
            frame_stride=frame_stride,
            draw_landmarks=True,
            include_image=True,
        )
    finally:
        cap.release()


def get_pose_from_video(video_path, process_width=720, frame_stride=2, include_image=True):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    try:
        yield from _pose_stream(
            cap,
            process_width=process_width,
            frame_stride=frame_stride,
            draw_landmarks=include_image,
            include_image=include_image,
        )
    finally:
        cap.release()
