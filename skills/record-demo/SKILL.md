---
name: record-demo
description: Record product demo videos with AI narration. Automates browser scenarios via Playwright, captures high-quality video via ffmpeg, and generates synchronized voice-over using ElevenLabs TTS.
trigger: when user asks to "record a demo", "make a product video", "create a demo recording", "record a walkthrough", or "screen record with narration"
dependencies:
  python:
    - ffmpeg
    - playwright
    - elevenlabs
---

# Record Demo Skill

Record polished product demo videos with automated browser interaction and AI voice-over narration.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Demo Script │───▶│  Recording   │───▶│ Post-Process│
│  (plan)      │    │  (capture)   │    │ (merge)     │
└─────────────┘    └──────────────┘    └─────────────┘
       │                  │                    │
   Actions +         Playwright          ffmpeg merge
   Narration         (headed) +          video + audio
   per step          ffmpeg crop         + timestamps
                     + timestamps
```

## Pipeline

### Stage 1: Script Generation
- User describes what to demo (e.g. "show creating a test case in OneTest")
- Agent writes a structured demo script:
  ```json
  {
    "title": "Creating a Test Case",
    "resolution": {"width": 1920, "height": 1080},
    "url": "https://app.onetest.ai",
    "steps": [
      {
        "action": "navigate",
        "target": "/test-cases",
        "narration": "Let's start from the Test Cases page.",
        "pause_after_ms": 1500
      },
      {
        "action": "click",
        "selector": "button:has-text('Create')",
        "narration": "Click the Create button to add a new test case.",
        "pause_after_ms": 2000
      }
    ]
  }
  ```
- Script is saved to `workspace/<date>/demo-script-<name>.json`
- **User reviews and approves the script before recording**

### Stage 2: Video Recording (Hybrid Approach)

**Why hybrid?** Playwright's built-in `recordVideo` produces low-quality WebM with no bitrate control. ffmpeg + avfoundation gives H.264 at any quality level.

**Method: Playwright headful + ffmpeg screen capture with crop**

1. **Launch Playwright in headed mode** at fixed window position:
   ```python
   browser = playwright.chromium.launch(
       headless=False,
       args=[
           f'--window-position=0,0',
           f'--window-size=1920,1080',
       ]
   )
   context = browser.new_context(
       viewport={"width": 1920, "height": 1080},
       # ALSO enable Playwright recordVideo as backup
       record_video_dir="videos/",
       record_video_size={"width": 1920, "height": 1080},
   )
   ```

2. **Start ffmpeg recording** (crop to browser window region):
   ```bash
   # macOS: avfoundation captures full screen, crop to browser window
   ffmpeg -f avfoundation -framerate 30 -i "<screen_idx>:none" \
       -vf "crop=1920:1080:0:0" \
       -c:v libx264 -crf 18 -preset slow \
       -pix_fmt yuv420p \
       output_raw.mp4
   ```

   **Getting screen device index:**
   ```bash
   ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep "Capture screen"
   # [6] Capture screen 0
   ```

   **Getting browser window position** (for crop offset):
   ```swift
   // Use CGWindowListCopyWindowInfo to find Chromium window bounds
   // WID, x, y, width, height
   ```

3. **Execute demo steps** with timestamp logging:
   ```python
   timestamps = []
   for step in script["steps"]:
       t = time.monotonic() - start_time
       timestamps.append({"time": t, "narration": step["narration"]})
       
       # Execute the action
       if step["action"] == "click":
           await page.click(step["selector"])
       elif step["action"] == "navigate":
           await page.goto(url + step["target"])
       elif step["action"] == "type":
           await page.fill(step["selector"], step["text"])
       
       # Deliberate pause (human-like pacing)
       await asyncio.sleep(step["pause_after_ms"] / 1000)
   ```

4. **Stop recording**: Send `q` to ffmpeg stdin, close browser context.

### Stage 3: Voice-Over Generation

Using ElevenLabs TTS (`sag` tool or direct API):

```python
for entry in timestamps:
    audio_segment = elevenlabs.generate(
        text=entry["narration"],
        voice="Rachel",  # or user-chosen voice
        model="eleven_turbo_v2",
    )
    save(f"narration_{idx}.mp3", audio_segment)
```

### Stage 4: Audio-Video Merge

Combine video + narration segments aligned to timestamps:

```bash
# 1. Create silent audio track matching video length
ffmpeg -i output_raw.mp4 -f lavfi -i anullsrc=r=44100:cl=stereo \
    -shortest -c:v copy -c:a aac silent_video.mp4

# 2. Mix narration segments at correct timestamps
# Build a complex filter that delays each narration:
ffmpeg -i silent_video.mp4 \
    -i narration_0.mp3 -i narration_1.mp3 -i narration_2.mp3 \
    -filter_complex "
        [1]adelay=0|0[a1];
        [2]adelay=3500|3500[a2];
        [3]adelay=7200|7200[a3];
        [a1][a2][a3]amix=inputs=3:duration=longest[aout]
    " \
    -map 0:v -map "[aout]" \
    -c:v copy -c:a aac \
    final_demo.mp4
```

### Stage 5: Optional Post-Processing

- **Title card**: ffmpeg drawtext overlay for first 3 seconds
- **Fade in/out**: `fade=t=in:st=0:d=0.5,fade=t=out:st=<end-0.5>:d=0.5`
- **Cursor highlighting**: Playwright can inject CSS for click ripple effects
- **Background music**: Mix low-volume background track

## Technical Notes

### Multi-Monitor Setup

**Problem**: Playwright opens windows on unpredictable monitors. ffmpeg avfoundation captures per-display. These must be coordinated.

**Solution: 3-layer approach**

1. **Detect monitors** (run at skill start):
   ```bash
   # List displays with resolution and position
   system_profiler SPDisplaysDataType 2>/dev/null | grep -E "Resolution|Main Display|Mirror"
   
   # More precise: use CoreGraphics
   swift -e '
   import CoreGraphics
   let displays = CGGetActiveDisplayList(10)
   // Returns display IDs with bounds (origin.x, origin.y, width, height)
   // Display at origin (0,0) is the "main" display
   // Secondary display might be at (1920, 0) or (-1920, 0) depending on arrangement
   '
   ```

   **Python helper to detect displays:**
   ```python
   import subprocess, re
   
   def get_displays() -> list[dict]:
       """Get display info via system_profiler."""
       result = subprocess.run(
           ["system_profiler", "SPDisplaysDataType"],
           capture_output=True, text=True
       )
       # Parse resolution, position, Retina status
       # Returns: [{"index": 0, "width": 3456, "height": 2234, "origin_x": 0, "retina": True}, ...]
   ```

2. **Map ffmpeg device index to target display**:
   ```bash
   ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep "Capture screen"
   # [6] Capture screen 0  ← typically main display
   # [7] Capture screen 1  ← secondary display
   ```
   
   Device index order matches `CGGetActiveDisplayList` order.
   Ask user which monitor to use, or default to secondary (keep primary free for other work).

3. **Force Playwright window to target monitor**:

   **Method A: Chromium args (sometimes works)**
   ```python
   # If secondary monitor is at x=1920 in global coords:
   browser = playwright.chromium.launch(
       headless=False,
       args=[
           '--window-position=1920,0',  # global coords for secondary monitor
           '--window-size=1920,1080',
       ]
   )
   ```

   **Method B: AppleScript reposition (reliable fallback)**
   ```python
   import subprocess, time
   
   # Launch browser first, wait for window to appear
   # Then force-move it:
   subprocess.run(['osascript', '-e', '''
       tell application "System Events"
           tell process "Chromium"
               set position of window 1 to {1920, 0}
               set size of window 1 to {1920, 1080}
           end tell
       end tell
   '''])
   ```
   
   **Method C: Full-screen on target display (cleanest for demos)**
   ```python
   # After navigation, press F11 or use Playwright to fullscreen
   await page.evaluate("document.documentElement.requestFullscreen()")
   # Or use AppleScript to fullscreen on specific display
   ```

4. **Retina / HiDPI handling**:
   - macOS reports logical resolution (e.g. 1728x1117) but physical is 2x (3456x2234)
   - Playwright viewport is in logical pixels
   - ffmpeg avfoundation captures at physical resolution
   - For 1080p output: set viewport to 1920x1080 logical, then ffmpeg will capture at 3840x2160, scale down:
     ```bash
     ffmpeg -f avfoundation -framerate 30 -i "7:none" \
         -vf "scale=1920:1080" \
         -c:v libx264 -crf 18 output.mp4
     ```
   - This actually gives BETTER quality — supersampled from Retina!

5. **Recommended workflow for multi-monitor**:
   ```
   User's primary monitor: normal work (IDE, chat, etc.)
   Secondary monitor: dedicated demo recording
   
   Agent:
   1. Detects secondary monitor (index, resolution, global position)
   2. Launches Playwright → moves window to secondary monitor
   3. ffmpeg records secondary monitor only (Capture screen 1)
   4. No crop needed — clean full-monitor capture
   5. Scale from Retina to 1080p for crisp output
   ```

### macOS Screen Recording Permission
- Terminal / iTerm needs "Screen Recording" permission in System Settings → Privacy & Security
- ffmpeg inherits permission from the parent terminal process
- After granting, terminal app needs restart

### ffmpeg avfoundation on macOS
- Device listing: `ffmpeg -f avfoundation -list_devices true -i "" 2>&1`
- Screen devices appear as "Capture screen 0", "Capture screen 1"
- Cannot target specific window (unlike X11's `-window_id`)
- Workaround: position Playwright window at known coordinates, use crop filter

### Playwright recordVideo (backup/fallback)
- Built-in: `browser.new_context(record_video_dir="videos/")`
- Outputs WebM, video available only after `context.close()`
- Quality limitations: no bitrate control, scaling issues reported
- Use as fallback if ffmpeg/avfoundation not available

### Window Position Detection (macOS)
```swift
import CoreGraphics
// Find Chromium window bounds
if let windows = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]] {
    for w in windows {
        if (w["kCGWindowOwnerName"] as? String)?.contains("Chrom") == true {
            let bounds = w["kCGWindowBounds"] as? [String: Any]
            // bounds["X"], bounds["Y"], bounds["Width"], bounds["Height"]
        }
    }
}
```

### ElevenLabs Voice-Over
- Use `sag` tool if available, or direct ElevenLabs Python SDK
- Recommended voices for demos: "Rachel" (professional), "Adam" (casual)
- Model: `eleven_turbo_v2` for fast generation, `eleven_multilingual_v2` for non-English
- Output: MP3 segments per narration step

## Available Tools on This Machine

Verified present:
- ✅ ffmpeg 8.0 (with avfoundation, libx264, libx265, aac)
- ✅ avfoundation screen capture devices: [6] Capture screen 0, [7] Capture screen 1
- ✅ ElevenLabs TTS (via `sag` / elevenlabs pip package)
- ✅ Playwright MCP server (v1.53.0-alpha, running as MCP tool)
- ⚠️ Screen Recording permission: granted but needs terminal restart

## Output

Final deliverable: `<name>_demo.mp4` in `workspace/<date>/`
- Resolution: 1920x1080 (default) or 3840x2160 (4K)
- Format: H.264 MP4 with AAC audio
- Includes: automated browser demo + synchronized AI narration

## Usage

```
User: Record a demo of creating a test case in OneTest
Agent: 
  1. Generates demo script → user reviews
  2. Records video (Playwright + ffmpeg)
  3. Generates voice-over (ElevenLabs)
  4. Merges and delivers final MP4
```
