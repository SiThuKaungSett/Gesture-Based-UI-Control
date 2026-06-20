# Gesture-Based UI Control

Gesture-Based UI Control is a Python desktop application that lets users control a Windows computer with hand gestures captured from a webcam.

The project uses MediaPipe for hand landmark detection, OpenCV for camera input and preview, and PyAutoGUI for mouse, keyboard, scrolling, zooming, and volume actions.

## Features

- Real-time hand tracking through a webcam
- Cursor movement using the index finger
- Left click, right click, double click, and drag gestures
- Scroll and zoom control
- Volume up and volume down gestures
- Active window minimize, restore, and maximize gestures
- Camera auto-detection for common Windows camera backends
- Live preview window with hand landmarks and current gesture status

## Demo Behavior

When the program runs, it opens a camera preview window. The app tracks one hand and shows green landmark points on the detected hand. A small label at the top of the preview shows the current gesture being recognized.

Press `Esc` in the preview window to close the program.

## Technologies Used

- Python
- MediaPipe
- OpenCV
- PyAutoGUI
- Windows `ctypes` APIs

## Requirements

- Windows operating system
- Python 3.10 or newer
- Webcam
- Good lighting for stable hand detection

## Installation

Clone the repository:

```powershell
git clone https://github.com/SiThuKaungSett/Gesture-Based-UI-Control.git
cd Gesture-Based-UI-Control
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the project:

```powershell
python main.py
```

## PyCharm Setup

1. Open the project folder in PyCharm.
2. Set the Python interpreter to `.venv`.
3. Install the packages from `requirements.txt`.
4. Run `main.py`.

## Gesture Controls

| Gesture | Action |
| --- | --- |
| Move index finger | Move cursor |
| Pinch thumb and index finger | Left click |
| Pinch thumb and middle finger | Right click |
| Pinch thumb, index, and middle finger | Drag |
| Hold thumb-only gesture | Double click |
| Thumb and index finger up | Control volume by moving hand up or down |
| Thumb, index, and middle finger up | Scroll or zoom |
| Thumb and pinky finger up | Minimize, restore, or maximize active window |

## Project Structure

```text
Gesture-Based-UI-Control/
|-- main.py
|-- requirements.txt
|-- README.md
|-- repo_description.txt
|-- .gitignore
```

## How It Works

The project has two main parts:

- `CaptureThread` opens the webcam, reads frames, detects hand landmarks with MediaPipe, and keeps the newest frame ready for processing.
- `GestureController` reads the landmarks, checks finger positions, detects gestures, moves the cursor, performs desktop actions, and updates the preview window.

Gesture distances are normalized using palm size. This makes detection more stable when the hand moves closer to or farther from the camera.

## Configuration

Most settings can be adjusted near the top of `main.py`.

Useful values to tune:

- `CAMERA_INDEX`
- `CAMERA_INDICES`
- `EMA_ALPHA`
- `ACTIVE_BOX_MARGIN`
- `PINCH_CLICK_THRESHOLD`
- `GRAB_THRESHOLD`
- `SCROLL_SENSITIVITY`
- `ZOOM_DEPTH_THRESHOLD`
- `VOLUME_MOVE_THRESHOLD`

## Troubleshooting

If the camera does not open:

- Close other apps using the camera, such as Zoom, Teams, or a browser.
- Check Windows camera privacy settings.
- Make sure PyCharm is using the correct virtual environment.
- Try changing `CAMERA_INDEX` in `main.py`.

If gestures are not stable:

- Improve the lighting.
- Keep your full hand visible in the camera frame.
- Move your hand more slowly.
- Tune the gesture thresholds in `main.py`.

If cursor movement feels reversed:

- Change `MIRROR_CURSOR_X` in `main.py`.

## Repository Description

Webcam-based hand gesture control for Windows using Python, MediaPipe, OpenCV, and PyAutoGUI.

## Author

Si Thu Kaung Sett
