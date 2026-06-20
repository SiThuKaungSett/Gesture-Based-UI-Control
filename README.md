# GestureProject

GestureProject is a webcam-based desktop control app that uses hand gestures to move the mouse, click, drag, scroll, zoom, adjust volume, and control the active Windows window.

It combines MediaPipe hand tracking, OpenCV camera capture, and PyAutoGUI desktop automation in one small Python project.

## Features

- Webcam hand tracking with MediaPipe
- Camera auto-detection across common Windows OpenCV backends
- Live OpenCV preview with landmark dots and current gesture status
- Cursor movement using the index fingertip
- Left click, right click, double click, and drag gestures
- Scroll and zoom gestures
- Volume up/down control
- Active window minimize, restore, and maximize control
- Refactored gesture handlers for easier tuning and future improvements

## Tech Stack

- Python
- OpenCV
- MediaPipe
- PyAutoGUI
- ctypes / Windows user32 APIs

## Requirements

- Windows
- Python 3.10 or newer
- A working webcam
- Good lighting for reliable hand detection

Install Python packages from `requirements.txt`:

```powershell
pip install -r requirements.txt
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

Press `Esc` in the camera preview window to exit.

## PyCharm Setup

1. Open the project folder in PyCharm.
2. Select the project interpreter from `.venv`.
3. Install packages from `requirements.txt` if PyCharm asks.
4. Run `main.py`.

## Gesture Controls

| Gesture | Action |
| --- | --- |
| Move index finger | Move cursor |
| Thumb + index pinch | Left click |
| Thumb + middle pinch | Right click |
| Thumb + index + middle pinch | Drag |
| Thumb only held for 2 seconds | Double click |
| Thumb + index | Volume up/down by vertical movement |
| Thumb + index + middle | Scroll or zoom |
| Thumb + pinky | Minimize, restore, or maximize active window |

The preview window shows the currently detected gesture at the top, which makes tuning and testing easier.

## Project Structure

```text
GestureProject/
├── main.py
├── requirements.txt
├── README.md
├── for_presentation.txt
├── repo_description.txt
└── .gitignore
```

## How It Works

`CaptureThread` opens the webcam, reads frames, and uses MediaPipe to detect one hand. It keeps only the newest frame so cursor movement stays responsive.

`GestureController` receives the latest frame and landmarks, calculates finger states, maps the index fingertip to the screen, and runs gesture-specific handlers such as `handle_scroll_zoom`, `handle_drag`, `handle_volume`, and `handle_window_control`.

Gesture distances are normalized by palm size, so the gestures remain more stable when the hand is closer to or farther from the camera.

## Configuration

Most tuning values are near the top of `main.py`.

Useful constants:

- `CAMERA_INDICES`: camera indexes to try
- `CAMERA_BACKENDS`: OpenCV backends to try
- `EMA_ALPHA`: cursor smoothing
- `ACTIVE_BOX_MARGIN`: camera margin used for cursor mapping
- `THUMB_EXT_THRESHOLD`: thumb detection threshold
- `PINCH_CLICK_THRESHOLD`: click pinch sensitivity
- `GRAB_THRESHOLD`: drag sensitivity
- `SCROLL_SENSITIVITY`: scroll sensitivity
- `ZOOM_DEPTH_THRESHOLD`: zoom sensitivity
- `VOLUME_MOVE_THRESHOLD`: volume gesture sensitivity

## Troubleshooting

If the camera does not open:

- Close apps that may already be using the camera, such as Zoom, Teams, or a browser.
- Check Windows camera privacy settings.
- Try changing `CAMERA_INDEX` or `CAMERA_INDICES` in `main.py`.
- Make sure PyCharm is using the correct `.venv` interpreter.

If gestures feel unstable:

- Improve lighting.
- Keep your full hand visible in the camera frame.
- Tune the threshold constants in `main.py`.
- Watch the gesture label in the preview window while testing.

If the cursor direction feels reversed:

- Change `MIRROR_CURSOR_X` in `main.py`.

## Git Notes

The `.gitignore` file excludes local development files such as `.venv`, `.idea`, `__pycache__`, logs, and tooling caches.

Recommended first commit:

```powershell
git add .
git commit -m "Prepare gesture control project"
```

## Short Repository Description

Webcam-based hand gesture control for Windows using Python, MediaPipe, OpenCV, and PyAutoGUI.
