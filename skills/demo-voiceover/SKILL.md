---
name: demo-voiceover
description: Generate synchronized voice-over narration for demo videos. Takes a demo script (from /demo-script) and a recorded video (from /record-demo), generates ElevenLabs TTS audio per scene with character-level timestamps, and merges everything into a final video with perfectly synced narration.
trigger: when user asks to "add voiceover", "generate narration", "add voice to video", "narrate the demo", "sync audio to video", or "create voice-over"
dependencies:
  python:
    - elevenlabs
    - ffmpeg
---

# Demo Voiceover Skill

Generate and synchronize AI voice-over narration for demo videos.

## How It Fits

This is the third stage of the demo video pipeline:

```
/demo-script  →  /record-demo  →  /demo-voiceover
  (plan)          (capture)         (narrate & deliver)
```

Can also be used standalone to add narration to any existing video + timestamp log.

## Inputs

The skill needs:

1. **Demo script JSON** — from `/demo-script` (`workspace/<date>/demo-script-<name>.json`)
2. **Raw video file** — from `/record-demo` (`workspace/<date>/<name>_raw.mp4`)
3. **Timestamp log** — from `/record-demo` (`workspace/<date>/<name>_timestamps.json`)

Timestamp log format (produced by `/record-demo`):
```json
{
  "video_file": "demo_raw.mp4",
  "start_epoch": 1739545200.0,
  "steps": [
    {
      "scene_id": "intro",
      "step_index": 0,
      "action": "navigate",
      "narration": "Welcome to OneTest. Let's create your first test case.",
      "timestamp_sec": 0.0,
      "completed_sec": 1.2
    },
    {
      "scene_id": "navigate-to-test-cases",
      "step_index": 0,
      "action": "click",
      "narration": "Open the Test Cases section from the sidebar.",
      "timestamp_sec": 3.2,
      "completed_sec": 3.8
    }
  ]
}
```

## Pipeline

### Stage 1: Narration Planning

Determine when each narration segment should play relative to the video:

**Timing strategy options:**

| Strategy | When narration starts | Best for |
|----------|----------------------|----------|
| `on_action` | At the moment the action begins (`timestamp_sec`) | Explaining what's about to happen |
| `after_action` | After the action completes (`completed_sec`) | Describing what just happened |
| `before_action` | 0.5s before the action begins | Building anticipation |
| `fill_pause` | During the `pause_after_ms` window | Narrating over the deliberate pause |

**Default: `fill_pause`** — narration plays during the pause after each action, so the viewer sees the action happen, then hears the explanation while the screen is stable. This feels the most natural.

**Planning output:**
```json
{
  "segments": [
    {
      "index": 0,
      "text": "Welcome to OneTest. Let's create your first test case.",
      "video_start_sec": 1.2,
      "max_duration_sec": 2.0
    },
    {
      "index": 1,
      "text": "Open the Test Cases section from the sidebar.",
      "video_start_sec": 3.8,
      "max_duration_sec": 1.5
    }
  ]
}
```

### Stage 2: Audio Generation (ElevenLabs)

Generate each narration segment using ElevenLabs **with-timestamps** endpoint.

**Why with-timestamps?**
- Returns character-level alignment data
- We know EXACTLY how long each segment is (to the millisecond)
- Enables subtitle generation for free
- Enables smart pacing adjustments

**API call per segment:**

```python
import httpx
import base64
import json

ELEVENLABS_API_KEY = "..."  # from env or config
VOICE_ID = "..."  # Rachel, Adam, etc.

async def generate_segment(
    text: str,
    index: int,
    previous_text: str | None = None,
    previous_request_ids: list[str] | None = None,
) -> dict:
    """Generate one narration segment with timestamps."""
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"
    
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # or eleven_turbo_v2 for speed
        "voice_settings": {
            "stability": 0.65,        # slightly varied = more natural
            "similarity_boost": 0.80,  # stay close to voice character
            "style": 0.15,            # subtle expressiveness
            "use_speaker_boost": True,
        },
        "output_format": "mp3_44100_128",
    }
    
    # Continuity: pass previous segment context
    # This makes transitions between segments sound natural,
    # not like separate recordings stitched together
    if previous_request_ids:
        payload["previous_request_ids"] = previous_request_ids[-3:]  # max 3
    elif previous_text:
        payload["previous_text"] = previous_text
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"xi-api-key": ELEVENLABS_API_KEY},
        )
        response.raise_for_status()
        data = response.json()
    
    # Decode audio
    audio_bytes = base64.b64decode(data["audio_base64"])
    audio_path = f"narration_{index:03d}.mp3"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
    
    # Extract duration from alignment
    alignment = data.get("alignment", {})
    char_end_times = alignment.get("character_end_times_seconds", [])
    duration_sec = max(char_end_times) if char_end_times else 0
    
    return {
        "index": index,
        "audio_path": audio_path,
        "duration_sec": duration_sec,
        "alignment": alignment,
        "request_id": response.headers.get("request-id", ""),
    }
```

**Generate all segments with continuity:**

```python
async def generate_all_narration(segments: list[dict]) -> list[dict]:
    """Generate all narration segments with cross-segment continuity."""
    results = []
    previous_request_ids = []
    
    for seg in segments:
        result = await generate_segment(
            text=seg["text"],
            index=seg["index"],
            previous_request_ids=previous_request_ids if previous_request_ids else None,
        )
        results.append(result)
        
        # Track request IDs for continuity chain
        if result["request_id"]:
            previous_request_ids.append(result["request_id"])
            # Keep only last 3 (API limit)
            previous_request_ids = previous_request_ids[-3:]
    
    return results
```

### Stage 3: Timing Reconciliation

After generating audio, reconcile planned timing with actual audio durations:

```python
def reconcile_timing(plan: list[dict], audio_results: list[dict]) -> list[dict]:
    """Adjust video timing to fit actual audio durations.
    
    Three scenarios per segment:
    1. Audio fits in available window → place at planned start
    2. Audio is shorter than window → place at planned start (extra silence is fine)
    3. Audio is LONGER than window → need to adjust
    
    For scenario 3, options:
    a) Speed up audio slightly (up to 1.15x before it sounds weird)
    b) Shift subsequent segments later (only works if there's slack)
    c) Trim narration text and re-generate (last resort)
    """
    timeline = []
    
    for plan_seg, audio in zip(plan, audio_results):
        available = plan_seg["max_duration_sec"]
        actual = audio["duration_sec"]
        
        entry = {
            "index": plan_seg["index"],
            "audio_path": audio["audio_path"],
            "video_start_sec": plan_seg["video_start_sec"],
            "audio_duration_sec": actual,
            "speed_factor": 1.0,
        }
        
        if actual > available * 1.15:
            # Audio way too long — flag for text shortening
            entry["warning"] = f"Audio ({actual:.1f}s) exceeds window ({available:.1f}s) by >{15}%"
            entry["speed_factor"] = min(actual / available, 1.15)  # cap at 1.15x
        elif actual > available:
            # Slightly over — speed up a tiny bit
            entry["speed_factor"] = actual / available
        
        timeline.append(entry)
    
    return timeline
```

### Stage 4: Audio Assembly

Merge all narration segments into a single audio track aligned to video timestamps:

```python
def build_ffmpeg_merge_command(
    video_path: str,
    timeline: list[dict],
    output_path: str,
    background_music: str | None = None,
) -> str:
    """Build ffmpeg command to merge video + narration + optional background music."""
    
    inputs = [f'-i "{video_path}"']
    filters = []
    
    # Add each narration segment as input
    for entry in timeline:
        inputs.append(f'-i "{entry["audio_path"]}"')
    
    # Build adelay filter for each segment
    audio_streams = []
    for i, entry in enumerate(timeline):
        input_idx = i + 1  # 0 is video
        delay_ms = int(entry["video_start_sec"] * 1000)
        stream_label = f"a{i}"
        
        # Apply speed adjustment if needed
        if entry["speed_factor"] != 1.0:
            tempo = entry["speed_factor"]
            filters.append(
                f'[{input_idx}]atempo={tempo:.3f},adelay={delay_ms}|{delay_ms}[{stream_label}]'
            )
        else:
            filters.append(
                f'[{input_idx}]adelay={delay_ms}|{delay_ms}[{stream_label}]'
            )
        audio_streams.append(f'[{stream_label}]')
    
    # Mix all narration streams
    n = len(audio_streams)
    mix_inputs = ''.join(audio_streams)
    filters.append(f'{mix_inputs}amix=inputs={n}:duration=longest:normalize=0[narration]')
    
    # Optional: add background music at low volume
    if background_music:
        bg_idx = len(timeline) + 1
        inputs.append(f'-i "{background_music}"')
        filters.append(f'[{bg_idx}]volume=0.08[bg]')  # very quiet
        filters.append('[narration][bg]amix=inputs=2:duration=shortest[aout]')
        audio_out = '[aout]'
    else:
        audio_out = '[narration]'
    
    filter_str = ';\n    '.join(filters)
    
    cmd = f'''ffmpeg {' '.join(inputs)} \\
    -filter_complex "
    {filter_str}
    " \\
    -map 0:v -map "{audio_out}" \\
    -c:v copy -c:a aac -b:a 192k \\
    -shortest \\
    "{output_path}"'''
    
    return cmd
```

**Execute:**
```bash
# Example generated command:
ffmpeg -i demo_raw.mp4 \
    -i narration_000.mp3 -i narration_001.mp3 -i narration_002.mp3 \
    -filter_complex "
        [1]adelay=1200|1200[a0];
        [2]adelay=3800|3800[a1];
        [3]atempo=1.08,adelay=7200|7200[a2];
        [a0][a1][a2]amix=inputs=3:duration=longest:normalize=0[narration]
    " \
    -map 0:v -map "[narration]" \
    -c:v copy -c:a aac -b:a 192k \
    -shortest \
    final_demo.mp4
```

### Stage 5: Subtitle Generation (Bonus)

Since we have character-level timestamps from ElevenLabs, generate SRT subtitles for free:

```python
def generate_srt(timeline: list[dict], audio_results: list[dict]) -> str:
    """Generate SRT subtitles from ElevenLabs alignment data."""
    srt_entries = []
    sub_index = 1
    
    for entry, audio in zip(timeline, audio_results):
        alignment = audio.get("alignment", {})
        chars = alignment.get("characters", [])
        start_times = alignment.get("character_start_times_seconds", [])
        end_times = alignment.get("character_end_times_seconds", [])
        
        if not chars:
            continue
        
        # Group into word-level chunks
        video_offset = entry["video_start_sec"]
        words = _group_chars_to_words(chars, start_times, end_times)
        
        # Group words into subtitle lines (max ~8 words per line)
        for line_words in _chunk_words(words, max_words=8):
            start = video_offset + line_words[0]["start"]
            end = video_offset + line_words[-1]["end"]
            text = " ".join(w["word"] for w in line_words)
            
            srt_entries.append(
                f"{sub_index}\n"
                f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n"
                f"{text}\n"
            )
            sub_index += 1
    
    return "\n".join(srt_entries)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

To burn subtitles into video:
```bash
ffmpeg -i final_demo.mp4 -vf subtitles=demo.srt \
    -c:v libx264 -crf 18 -c:a copy \
    final_demo_subtitled.mp4
```

Or keep as separate .srt file for optional display.

## Voice Configuration

### Recommended Voices

| Voice | Style | Best for |
|-------|-------|----------|
| Rachel | Professional, warm | Product demos, marketing |
| Adam | Clear, authoritative | Technical walkthroughs |
| Bella | Friendly, upbeat | Onboarding tutorials |
| Antoni | Calm, measured | Enterprise demos |

### Voice Settings Explained

```json
{
  "stability": 0.65,         // 0=varied, 1=monotone. 0.5-0.7 is natural for demos
  "similarity_boost": 0.80,  // How close to original voice. Higher = more consistent
  "style": 0.15,             // Expressiveness. Keep low for demos (too high = dramatic)
  "use_speaker_boost": true  // Clarity enhancement. Always on for demos
}
```

### Model Selection

| Model | Speed | Quality | Languages | Cost | Use when |
|-------|-------|---------|-----------|------|----------|
| `eleven_multilingual_v2` | Slower | Best | 29 languages | 1x | Final production |
| `eleven_turbo_v2` | Fast | Good | English only | 0.5x | Drafts, iteration |
| `eleven_flash_v2_5` | Fastest | Good | Multilingual | 0.5x | Quick previews |

**Recommendation:** Use `eleven_turbo_v2` for draft iterations, switch to `eleven_multilingual_v2` for final render.

## Continuity Between Segments

ElevenLabs supports request stitching to make segments sound like one continuous narration:

```
Segment 1: "Welcome to OneTest."
    → request_id: "abc123"

Segment 2: "Let's create a test case."
    → previous_request_ids: ["abc123"]
    → request_id: "def456"

Segment 3: "Click the Create button."
    → previous_request_ids: ["abc123", "def456"]
    → request_id: "ghi789"
```

This avoids the "stitched together" sound where each segment starts with fresh intonation. The voice flows naturally across cuts.

**Fallback:** If request IDs aren't available (re-generation), use `previous_text` / `next_text`:
```json
{
  "text": "Let's create a test case.",
  "previous_text": "Welcome to OneTest.",
  "next_text": "Click the Create button."
}
```

## Pacing Adjustments

If narration doesn't fit the video timing:

| Problem | Solution | Limit |
|---------|----------|-------|
| Audio slightly too long | Speed up with `atempo` filter | Max 1.15x (beyond this sounds rushed) |
| Audio way too long | Shorten narration text, re-generate | Re-generate segment only |
| Audio too short | Add silence padding (natural) | N/A — silence during demos is fine |
| Awkward gap between segments | Extend pause or add transition phrase | Keep pauses ≤ 3s |

**Speed adjustment in ffmpeg:**
```bash
# Speed up by 10%
-filter_complex "[1]atempo=1.10[a1]"

# Slow down by 10% (rare, but possible)
-filter_complex "[1]atempo=0.90[a1]"
```

## Output Files

| File | Description |
|------|-------------|
| `<name>_final.mp4` | Video + narration merged |
| `<name>_final_subtitled.mp4` | Video + narration + burned-in subtitles |
| `<name>.srt` | Subtitle file (separate) |
| `<name>_narration_full.mp3` | Full narration audio track (for reuse) |
| `narration_NNN.mp3` | Individual segments (for re-generation) |
| `<name>_voiceover_plan.json` | Timing plan (for debugging/iteration) |

All saved to `workspace/<date>/`

## Iteration Workflow

The skill supports re-doing individual segments without regenerating everything:

1. User reviews video: "The narration on scene 3 is too fast"
2. Agent adjusts: shorten text, re-generate only segment 3
3. Use `previous_request_ids` from segments 1-2 for continuity
4. Re-merge with ffmpeg (only audio track changes, video stays)

This is fast because:
- Video doesn't need re-recording
- Only one ElevenLabs API call per changed segment
- ffmpeg merge is seconds
