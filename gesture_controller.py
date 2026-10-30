import cv2
import mediapipe as mp
import numpy as np
import time
import math
import pyautogui
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

def get_volume_controller():
    device = AudioUtilities.GetSpeakers()
    if hasattr(device, '_dev') and device._dev is not None:
        raw_device = device._dev
    elif hasattr(device, 'endpoint') and device.endpoint is not None:
        raw_device = device.endpoint
    else:
        raw_device = device

    interface = raw_device.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    return cast(interface, POINTER(IAudioEndpointVolume))

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]

def main():
    volume = get_volume_controller()
    vol_range = volume.GetVolumeRange()
    min_vol, max_vol = vol_range[0], vol_range[1]

    screen_w, screen_h = pyautogui.size()

    # MediaPipe Hand Landmarker
    base_options = mp_python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    # 1280x720 Capture
    cap = cv2.VideoCapture(0)
    cam_w, cam_h = 1280, 720
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)

    # Drawing Canvas layer
    canvas = np.zeros((cam_h, cam_w, 3), dtype=np.uint8)
    draw_prev_x, draw_prev_y = 0, 0

    frame_reduction = 140
    smoothening = 5
    curr_x, curr_y = 0, 0
    prev_x, prev_y = 0, 0
    prev_scroll_y = 0

    p_time = 0
    vol_bar = 550
    vol_pct = 0
    frame_timestamp_ms = 0
    last_click_time = 0

    print("Air-Canvas & Gesture HCI running. Press 'q' to exit.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        frame_timestamp_ms += 33
        result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

        lm_list = []
        if result.hand_landmarks:
            for hand_lms in result.hand_landmarks:
                for idx, lm in enumerate(hand_lms):
                    cx, cy = int(lm.x * cam_w), int(lm.y * cam_h)
                    lm_list.append((idx, cx, cy))
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 0), cv2.FILLED)

                for start_idx, end_idx in HAND_CONNECTIONS:
                    pt1 = (lm_list[start_idx][1], lm_list[start_idx][2])
                    pt2 = (lm_list[end_idx][1], lm_list[end_idx][2])
                    cv2.line(frame, pt1, pt2, (255, 255, 0), 2)

        mode_text = "STANDBY"

        if len(lm_list) >= 21:
            x_thumb, y_thumb = lm_list[4][1], lm_list[4][2]
            x_index, y_index = lm_list[8][1], lm_list[8][2]
            x_mid, y_mid = lm_list[12][1], lm_list[12][2]
            x_ring, y_ring = lm_list[16][1], lm_list[16][2]
            x_pinky, y_pinky = lm_list[20][1], lm_list[20][2]

            # Detect individual finger extensions
            thumb_up = lm_list[4][0] > lm_list[3][0] or math.hypot(x_thumb - x_index, y_thumb - y_index) > 60
            index_up = lm_list[8][2] < lm_list[6][2]
            middle_up = lm_list[12][2] < lm_list[10][2]
            ring_up = lm_list[16][2] < lm_list[14][2]
            pinky_up = lm_list[20][2] < lm_list[18][2]

            thumb_index_dist = math.hypot(x_index - x_thumb, y_index - y_thumb)
            mid_index_dist = math.hypot(x_mid - x_index, y_mid - y_index)

            # ---------------- 1. CLEAR CANVAS (Fist) ----------------
            if not index_up and not middle_up and not ring_up and not pinky_up:
                mode_text = "CLEAR CANVAS"
                canvas = np.zeros((cam_h, cam_w, 3), dtype=np.uint8)
                draw_prev_x, draw_prev_y = 0, 0

            # ---------------- 2. AIR-CANVAS DRAWING ----------------
            # Pinch thumb & index closely and move to paint
            elif thumb_index_dist < 38 and not ring_up and not pinky_up:
                mode_text = "AIR DRAWING"
                cx, cy = (x_thumb + x_index) // 2, (y_thumb + y_index) // 2
                cv2.circle(frame, (cx, cy), 10, (0, 0, 255), cv2.FILLED)

                if draw_prev_x == 0 and draw_prev_y == 0:
                    draw_prev_x, draw_prev_y = cx, cy

                cv2.line(canvas, (draw_prev_x, draw_prev_y), (cx, cy), (0, 255, 255), 6)
                draw_prev_x, draw_prev_y = cx, cy

            # ---------------- 3. SCROLLING MODE (Index & Middle Up & Separated) ----------------
            elif index_up and middle_up and mid_index_dist >= 45 and not ring_up and not pinky_up:
                mode_text = "SCROLL MODE"
                draw_prev_x, draw_prev_y = 0, 0
                avg_y = (y_index + y_mid) // 2

                if prev_scroll_y != 0:
                    dy = prev_scroll_y - avg_y
                    if abs(dy) > 12:
                        scroll_amount = int(dy * 2.5)
                        pyautogui.scroll(scroll_amount)
                prev_scroll_y = avg_y

            # ---------------- 4. LEFT CLICK (Index & Middle Pinched Together) ----------------
            elif index_up and middle_up and mid_index_dist < 35 and not ring_up and not pinky_up:
                mode_text = "LEFT CLICK"
                draw_prev_x, draw_prev_y = 0, 0
                if (time.time() - last_click_time) > 0.35:
                    pyautogui.click()
                    last_click_time = time.time()
                    cv2.circle(frame, ((x_index + x_mid) // 2, (y_index + y_mid) // 2), 14, (0, 0, 255), cv2.FILLED)

            # ---------------- 5. MOUSE CURSOR GLIDE (Index Only Up) ----------------
            elif index_up and not middle_up and not ring_up and not pinky_up:
                mode_text = "MOUSE MOVE"
                draw_prev_x, draw_prev_y = 0, 0
                prev_scroll_y = 0

                target_x = np.interp(x_index, (frame_reduction, cam_w - frame_reduction), (0, screen_w))
                target_y = np.interp(y_index, (frame_reduction, cam_h - frame_reduction), (0, screen_h))

                curr_x = prev_x + (target_x - prev_x) / smoothening
                curr_y = prev_y + (target_y - prev_y) / smoothening

                pyautogui.moveTo(curr_x, curr_y)
                prev_x, prev_y = curr_x, curr_y
                cv2.circle(frame, (x_index, y_index), 9, (255, 0, 0), cv2.FILLED)

            # ---------------- 6. VOLUME MODULATION ----------------
            elif thumb_index_dist > 45 and not middle_up and not ring_up and not pinky_up:
                mode_text = "VOLUME ADJUST"
                draw_prev_x, draw_prev_y = 0, 0
                vol = np.interp(thumb_index_dist, [45, 220], [min_vol, max_vol])
                vol_bar = np.interp(thumb_index_dist, [45, 220], [550, 350])
                vol_pct = np.interp(thumb_index_dist, [45, 220], [0, 100])
                volume.SetMasterVolumeLevel(vol, None)
                cv2.line(frame, (x_thumb, y_thumb), (x_index, y_index), (0, 255, 255), 3)

            else:
                draw_prev_x, draw_prev_y = 0, 0
                prev_scroll_y = 0
        else:
            draw_prev_x, draw_prev_y = 0, 0
            prev_scroll_y = 0

        # Merge drawing canvas seamlessly over the live webcam feed
        img_gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        _, img_inv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
        img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
        frame = cv2.bitwise_and(frame, img_inv)
        frame = cv2.bitwise_or(frame, canvas)

        # HUD Indicators
        cv2.putText(frame, f"MODE: {mode_text}", (40, 60), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 255), 2)

        # Volume Visualizer
        cv2.rectangle(frame, (1210, 350), (1245, 550), (0, 255, 0), 2)
        cv2.rectangle(frame, (1210, int(vol_bar)), (1245, 550), (0, 255, 0), cv2.FILLED)
        cv2.putText(frame, f'{int(vol_pct)}%', (1190, 580), cv2.FONT_HERSHEY_PLAIN, 1.4, (0, 255, 0), 2)

        # Interaction Boundary Box
        cv2.rectangle(frame, (frame_reduction, frame_reduction),
                      (cam_w - frame_reduction, cam_h - frame_reduction), (255, 0, 255), 1)

        # Real-time FPS
        c_time = time.time()
        fps = 1 / (c_time - p_time) if (c_time - p_time) > 0 else 0
        p_time = c_time
        cv2.putText(frame, f'FPS: {int(fps)}', (cam_w - 140, 60), cv2.FONT_HERSHEY_PLAIN, 1.8, (255, 0, 0), 2)

        cv2.imshow("Air-Canvas & Gesture HCI Engine", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()