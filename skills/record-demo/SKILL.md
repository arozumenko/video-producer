---
name: record-demo
description: Record product demo videos with automated browser interaction and screen capture. Use when user asks to "record a demo", "make a product video", "create a demo recording", "record a walkthrough", or "screen record with narration". Captures H.264 video via Playwright headful + ffmpeg avfoundation with action timestamps for voice-over sync.
compatibility: Requires ffmpeg with avfoundation (macOS), Playwright MCP server, and Screen Recording permission.
metadata:
  author: arozumenko
  version: 1.0.0
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

Run `python scripts/detect_displays.py` to detect monitors and ffmpeg device indices.

For detailed multi-monitor workflow (window positioning, Retina handling, AppleScript fallback), consult `references/multi-monitor.md`.

### macOS Screen Recording Permission
- Terminal / iTerm needs "Screen Recording" in System Settings -> Privacy & Security
- ffmpeg inherits permission from parent terminal process
- After granting, terminal app needs restart

### Playwright recordVideo (backup/fallback)
- Built-in: `browser.new_context(record_video_dir="videos/")`
- Lower quality than ffmpeg — use as fallback only

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
