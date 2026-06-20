import ctypes
import math
import queue
import threading
import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import pyautogui


# --- CAMERA SETTINGS ---
CAMERA_INDEX = 0
CAMERA_INDICES = (CAMERA_INDEX, 1, 2, 3)
CAMERA_BACKENDS = (
    ("DirectShow", cv2.CAP_DSHOW),
    ("Media Foundation", cv2.CAP_MSMF),
    ("OpenCV default", cv2.CAP_ANY),
)
MAX_FAILED_READS = 60

# --- TRACKING SETTINGS ---
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7
THUMB_HYSTERESIS = 2

# --- CURSOR SETTINGS ---
EMA_ALPHA = 0.2
ACTIVE_BOX_MARGIN = 0.15
MIRROR_CURSOR_X = True

# --- GESTURE THRESHOLDS ---
THUMB_EXT_THRESHOLD = 0.35
PINCH_CLICK_THRESHOLD = 0.12
GRAB_THRESHOLD = 0.25
SCROLL_SENSITIVITY = 0.06
ZOOM_DEPTH_THRESHOLD = 0.18
WINDOW_MOVE_THRESHOLD = 0.18
VOLUME_MOVE_THRESHOLD = 0.2
DOUBLE_CLICK_HOLD_SECONDS = 2.0

# --- COOLDOWNS ---
CLICK_COOLDOWN = 0.4
DOUBLE_CLICK_COOLDOWN = 0.6
ZOOM_COOLDOWN = 0.4
VOLUME_COOLDOWN = 0.3
WINDOW_COOLDOWN = 0.7
SCROLL_COOLDOWN = 0.05

WINDOW_TITLE = "Hand Control"
ESC_KEY = 27

WRIST = 0
THUMB_IP = 3
THUMB_TIP = 4
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
SCREEN_W, SCREEN_H = pyautogui.size()


@dataclass
class FramePacket:
    frame: object
    landmarks: list
    error: str = ""


@dataclass
class FingerState:
    index: bool
    middle: bool
    ring: bool
    pinky: bool
    thumb: bool
    stable_thumb: bool
    thumb_index_distance: float
    thumb_middle_distance: float


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clamp(value, low, high):
    return max(low, min(value, high))


def open_camera():
    for index in CAMERA_INDICES:
        for backend_name, backend in CAMERA_BACKENDS:
            cap = cv2.VideoCapture(index, backend)
            if not cap.isOpened():
                cap.release()
                continue

            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"Camera opened: index {index} using {backend_name}")
                return cap

            cap.release()

    return None


def put_latest(out_queue, packet):
    try:
        if out_queue.full():
            out_queue.get_nowait()
        out_queue.put_nowait(packet)
    except queue.Full:
        pass


class CaptureThread(threading.Thread):
    def __init__(self, out_queue, stop_event):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self.stop_event = stop_event
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
        )

    def run(self):
        cap = open_camera()
        if cap is None:
            put_latest(
                self.out_queue,
                FramePacket(
                    frame=None,
                    landmarks=[],
                    error=(
                        "Could not open a camera. Check Windows camera privacy settings, "
                        "close Zoom/Teams/browser camera tabs, then try again."
                    ),
                ),
            )
            return

        failed_reads = 0
        try:
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    failed_reads += 1
                    if failed_reads >= MAX_FAILED_READS:
                        put_latest(
                            self.out_queue,
                            FramePacket(
                                frame=None,
                                landmarks=[],
                                error=(
                                    "The camera opened, but stopped sending frames. "
                                    "Reconnect the camera or close other apps using it."
                                ),
                            ),
                        )
                        break
                    time.sleep(0.03)
                    continue

                failed_reads = 0
                landmarks = self.detect_landmarks(frame)
                put_latest(self.out_queue, FramePacket(frame=frame, landmarks=landmarks))
        finally:
            cap.release()
            self.hands.close()

    def detect_landmarks(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        if not result.multi_hand_landmarks:
            return []

        height, width = frame.shape[:2]
        hand = result.multi_hand_landmarks[0]
        return [(lm.x * width, lm.y * height) for lm in hand.landmark]


class GestureController:
    def __init__(self, in_queue):
        self.in_queue = in_queue
        self.ema_x = None
        self.ema_y = None
        self.last_action = {
            "left": 0.0,
            "right": 0.0,
            "double": 0.0,
            "zoom": 0.0,
            "vol": 0.0,
            "win": 0.0,
            "scroll": 0.0,
        }
        self.is_dragging = False
        self.prev_vol_y = None
        self.prev_win_y = None
        self.prev_scroll_y = None
        self.prev_palm_size = None
        self.thumb_up_counter = 0
        self.thumb_hold_start = None
        self.current_gesture = "Searching"

    def process(self):
        while True:
            packet = self.in_queue.get()
            if packet.error:
                print(packet.error)
                break

            if self.handle_frame(packet):
                break

    def handle_frame(self, packet):
        frame = packet.frame
        landmarks = packet.landmarks
        now = time.time()

        if not landmarks:
            self.current_gesture = "No hand"
            self.reset_motion_state()
            self.release_drag()
            return self.show_frame(frame)

        palm_size = max(distance(landmarks[WRIST], landmarks[MIDDLE_MCP]), 1.0)
        fingers = self.get_finger_state(landmarks, palm_size)

        self.move_cursor(landmarks, frame.shape)
        self.current_gesture = self.run_gesture(landmarks, fingers, palm_size, now)
        self.draw_landmarks(frame, landmarks)
        return self.show_frame(frame)

    def get_finger_state(self, landmarks, palm_size):
        index_up = landmarks[INDEX_TIP][1] < landmarks[INDEX_PIP][1]
        middle_up = landmarks[MIDDLE_TIP][1] < landmarks[MIDDLE_PIP][1]
        ring_up = landmarks[RING_TIP][1] < landmarks[RING_PIP][1]
        pinky_up = landmarks[PINKY_TIP][1] < landmarks[PINKY_PIP][1]

        thumb_distance = distance(landmarks[THUMB_TIP], landmarks[WRIST]) / palm_size
        thumb_tip_above_ip = landmarks[THUMB_TIP][1] < landmarks[THUMB_IP][1]
        thumb_up = thumb_tip_above_ip or thumb_distance > THUMB_EXT_THRESHOLD

        if thumb_up:
            self.thumb_up_counter = min(THUMB_HYSTERESIS, self.thumb_up_counter + 1)
        else:
            self.thumb_up_counter = max(0, self.thumb_up_counter - 1)

        return FingerState(
            index=index_up,
            middle=middle_up,
            ring=ring_up,
            pinky=pinky_up,
            thumb=thumb_up,
            stable_thumb=self.thumb_up_counter >= THUMB_HYSTERESIS,
            thumb_index_distance=distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / palm_size,
            thumb_middle_distance=distance(landmarks[THUMB_TIP], landmarks[MIDDLE_TIP]) / palm_size,
        )

    def move_cursor(self, landmarks, frame_shape):
        height, width = frame_shape[:2]
        raw_x, raw_y = landmarks[INDEX_TIP]

        if self.ema_x is None:
            self.ema_x, self.ema_y = raw_x, raw_y

        self.ema_x = EMA_ALPHA * raw_x + (1 - EMA_ALPHA) * self.ema_x
        self.ema_y = EMA_ALPHA * raw_y + (1 - EMA_ALPHA) * self.ema_y

        margin_x = width * ACTIVE_BOX_MARGIN
        margin_y = height * ACTIVE_BOX_MARGIN
        norm_x = (clamp(self.ema_x, margin_x, width - margin_x) - margin_x) / (width - 2 * margin_x)
        norm_y = (clamp(self.ema_y, margin_y, height - margin_y) - margin_y) / (height - 2 * margin_y)

        screen_x = (1 - norm_x) * SCREEN_W if MIRROR_CURSOR_X else norm_x * SCREEN_W
        pyautogui.moveTo(int(screen_x), int(norm_y * SCREEN_H))

    def run_gesture(self, landmarks, fingers, palm_size, now):
        if self.is_scroll_zoom_pose(fingers):
            return self.handle_scroll_zoom(landmarks, palm_size, now)

        if self.is_double_click_pose(fingers):
            return self.handle_double_click(now)

        if self.is_window_pose(fingers):
            return self.handle_window_control(landmarks, palm_size, now)

        if self.is_drag_pose(fingers):
            return self.handle_drag()

        if self.is_volume_pose(fingers):
            return self.handle_volume(landmarks, palm_size, now)

        if self.is_ready("left", CLICK_COOLDOWN, now) and fingers.thumb_index_distance < PINCH_CLICK_THRESHOLD:
            pyautogui.click()
            self.last_action["left"] = now
            return "Left click"

        if self.is_ready("right", CLICK_COOLDOWN, now) and fingers.thumb_middle_distance < PINCH_CLICK_THRESHOLD:
            pyautogui.click(button="right")
            self.last_action["right"] = now
            return "Right click"

        self.reset_motion_state()
        self.release_drag()
        if not fingers.thumb:
            self.thumb_up_counter = max(0, self.thumb_up_counter - 1)
        return "Cursor"

    def is_scroll_zoom_pose(self, fingers):
        return fingers.stable_thumb and fingers.index and fingers.middle and not fingers.ring and not fingers.pinky

    def is_double_click_pose(self, fingers):
        return fingers.stable_thumb and not fingers.index and not fingers.middle and not fingers.ring and not fingers.pinky

    def is_window_pose(self, fingers):
        return fingers.stable_thumb and fingers.pinky and not fingers.index and not fingers.middle and not fingers.ring

    def is_drag_pose(self, fingers):
        return fingers.thumb_index_distance < GRAB_THRESHOLD and fingers.thumb_middle_distance < GRAB_THRESHOLD

    def is_volume_pose(self, fingers):
        return fingers.stable_thumb and fingers.index and not fingers.middle and not fingers.ring and not fingers.pinky

    def handle_scroll_zoom(self, landmarks, palm_size, now):
        hand_y = (landmarks[WRIST][1] + landmarks[MIDDLE_MCP][1]) / 2

        if self.prev_palm_size is not None:
            depth_change = (palm_size - self.prev_palm_size) / self.prev_palm_size
            if abs(depth_change) > ZOOM_DEPTH_THRESHOLD and self.is_ready("zoom", ZOOM_COOLDOWN, now):
                if depth_change > 0:
                    self.zoom_in()
                    gesture = "Zoom in"
                else:
                    pyautogui.hotkey("ctrl", "-")
                    gesture = "Zoom out"

                self.last_action["zoom"] = now
                self.prev_scroll_y = hand_y
                self.prev_palm_size = palm_size
                return gesture

        if self.prev_scroll_y is not None:
            vertical_change = (self.prev_scroll_y - hand_y) / palm_size
            if abs(vertical_change) > SCROLL_SENSITIVITY and self.is_ready("scroll", SCROLL_COOLDOWN, now):
                pyautogui.scroll(180 if vertical_change > 0 else -180)
                self.last_action["scroll"] = now
                self.prev_scroll_y = hand_y
                self.prev_palm_size = palm_size
                return "Scroll up" if vertical_change > 0 else "Scroll down"
        else:
            self.prev_scroll_y = hand_y

        self.prev_palm_size = palm_size
        return "Scroll/zoom ready"

    def handle_double_click(self, now):
        if self.thumb_hold_start is None:
            self.thumb_hold_start = now

        if (
            now - self.thumb_hold_start >= DOUBLE_CLICK_HOLD_SECONDS
            and self.is_ready("double", DOUBLE_CLICK_COOLDOWN, now)
        ):
            pyautogui.doubleClick()
            self.last_action["double"] = now
            self.thumb_hold_start = None
            return "Double click"

        return "Double click hold"

    def handle_window_control(self, landmarks, palm_size, now):
        hand_y = (landmarks[WRIST][1] + landmarks[MIDDLE_MCP][1]) / 2

        if self.prev_win_y is not None:
            vertical_change = (self.prev_win_y - hand_y) / palm_size
            if abs(vertical_change) > WINDOW_MOVE_THRESHOLD and self.is_ready("win", WINDOW_COOLDOWN, now):
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                is_minimized = ctypes.windll.user32.IsIconic(hwnd)

                if vertical_change > 0:
                    ctypes.windll.user32.ShowWindow(hwnd, 9 if is_minimized else 3)
                    gesture = "Restore/maximize"
                else:
                    ctypes.windll.user32.ShowWindow(hwnd, 6)
                    gesture = "Minimize"

                self.last_action["win"] = now
                self.prev_win_y = hand_y
                return gesture

        self.prev_win_y = hand_y
        return "Window ready"

    def handle_drag(self):
        if not self.is_dragging:
            pyautogui.mouseDown()
            self.is_dragging = True
        return "Drag"

    def handle_volume(self, landmarks, palm_size, now):
        wrist_y = landmarks[WRIST][1]

        if self.prev_vol_y is not None:
            vertical_change = (self.prev_vol_y - wrist_y) / palm_size
            if abs(vertical_change) > VOLUME_MOVE_THRESHOLD and self.is_ready("vol", VOLUME_COOLDOWN, now):
                pyautogui.press("volumeup" if vertical_change > 0 else "volumedown")
                self.last_action["vol"] = now
                self.prev_vol_y = wrist_y
                return "Volume up" if vertical_change > 0 else "Volume down"
        else:
            self.prev_vol_y = wrist_y

        return "Volume ready"

    def zoom_in(self):
        try:
            pyautogui.hotkey("ctrl", "=")
        except Exception:
            pyautogui.keyDown("ctrl")
            pyautogui.press("+")
            pyautogui.keyUp("ctrl")

    def reset_motion_state(self):
        self.prev_vol_y = None
        self.prev_win_y = None
        self.prev_scroll_y = None
        self.prev_palm_size = None
        self.thumb_hold_start = None

    def release_drag(self):
        if self.is_dragging:
            pyautogui.mouseUp()
            self.is_dragging = False

    def is_ready(self, action, cooldown, now):
        return now - self.last_action[action] > cooldown

    def draw_landmarks(self, frame, landmarks):
        for point in landmarks:
            cv2.circle(frame, (int(point[0]), int(point[1])), 3, (0, 255, 0), -1)

    def show_frame(self, frame):
        self.draw_overlay(frame)
        cv2.imshow(WINDOW_TITLE, cv2.flip(frame, 1))
        return cv2.waitKey(1) == ESC_KEY

    def draw_overlay(self, frame):
        cv2.rectangle(frame, (8, 8), (245, 48), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"Gesture: {self.current_gesture}",
            (16, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )


def main():
    frame_queue = queue.Queue(maxsize=1)
    stop_event = threading.Event()
    capture = CaptureThread(frame_queue, stop_event)
    capture.start()

    try:
        GestureController(frame_queue).process()
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as error:
        print(f"Error: {error}")
    finally:
        stop_event.set()
        capture.join()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
