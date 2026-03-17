# Multi-Monitor Recording Setup

## Overview

Playwright opens windows on unpredictable monitors. ffmpeg avfoundation captures per-display. These must be coordinated.

## 3-Layer Approach

### 1. Detect monitors

```bash
# List displays with resolution and position
system_profiler SPDisplaysDataType 2>/dev/null | grep -E "Resolution|Main Display|Mirror"

# Or use the helper script:
python scripts/detect_displays.py
```

### 2. Map ffmpeg device index to target display

```bash
ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep "Capture screen"
# [6] Capture screen 0  <- typically main display
# [7] Capture screen 1  <- secondary display
```

Device index order matches `CGGetActiveDisplayList` order.

### 3. Force Playwright window to target monitor

**Method A: Chromium args**
```python
browser = playwright.chromium.launch(
    headless=False,
    args=['--window-position=1920,0', '--window-size=1920,1080']
)
```

**Method B: AppleScript reposition (reliable fallback)**
```python
subprocess.run(['osascript', '-e', '''
    tell application "System Events"
        tell process "Chromium"
            set position of window 1 to {1920, 0}
            set size of window 1 to {1920, 1080}
        end tell
    end tell
'''])
```

**Method C: Full-screen on target display (cleanest)**
```python
await page.evaluate("document.documentElement.requestFullscreen()")
```

### 4. Retina / HiDPI handling

- macOS reports logical resolution (1728x1117) but physical is 2x (3456x2234)
- Playwright viewport = logical pixels
- ffmpeg avfoundation captures at physical resolution
- For 1080p output from Retina: set viewport to 1920x1080, then scale down:
  ```bash
  ffmpeg -f avfoundation -framerate 30 -i "7:none" \
      -vf "scale=1920:1080" \
      -c:v libx264 -crf 18 output.mp4
  ```
- This gives BETTER quality — supersampled from Retina

### 5. Recommended workflow

```
User's primary monitor: normal work (IDE, chat)
Secondary monitor: dedicated demo recording

Agent:
1. Detects secondary monitor (index, resolution, global position)
2. Launches Playwright -> moves window to secondary monitor
3. ffmpeg records secondary monitor only (Capture screen 1)
4. No crop needed — clean full-monitor capture
5. Scale from Retina to 1080p for crisp output
```

## macOS Screen Recording Permission

- Terminal / iTerm needs "Screen Recording" in System Settings -> Privacy & Security
- ffmpeg inherits permission from parent terminal process
- After granting, terminal app needs restart
