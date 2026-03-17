---
name: demo-voiceover
description: Generate and synchronize AI voice-over narration for demo videos using ElevenLabs TTS. Use when user asks to "add voiceover", "generate narration", "add voice to video", "narrate the demo", or "create voice-over". Produces per-scene audio with character-level timestamps, automatic subtitle generation, and continuity chaining across segments.
compatibility: Requires ElevenLabs API key (ELEVENLABS_API_KEY) and ffmpeg for audio-video merge.
metadata:
  author: arozumenko
  version: 1.0.0
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

Generate each narration segment using ElevenLabs **with-timestamps** endpoint:
- Returns character-level alignment (exact duration to the millisecond)
- Enables subtitle generation for free
- Supports continuity chaining via `previous_request_ids` (max 3)

Run `python scripts/generate_narration.py --plan voiceover_plan.json --voice rachel --output-dir .`

For API details, consult `references/elevenlabs-api.md`.

### Stage 3: Timing Reconciliation

After generating audio, reconcile planned vs actual durations:

1. **Audio fits** in available window -> place at planned start
2. **Audio shorter** -> extra silence is fine (demos breathe)
3. **Audio longer** -> speed up (max 1.15x via `atempo`), or shorten text and re-generate

Cap speed adjustment at 1.15x — beyond that sounds rushed.

### Stage 4: Audio Assembly

Merge narration segments with video using the helper script:

```bash
bash scripts/merge_audio_video.sh demo_raw.mp4 narration_results.json final_demo.mp4
```

The script builds an ffmpeg `filter_complex` with `adelay` per segment and `atempo` for speed adjustments.

### Stage 5: Subtitle Generation

Character-level timestamps from ElevenLabs enable free SRT generation:
- Group characters into words, words into subtitle lines (max 8 words)
- Offset by `video_start_sec` for each segment
- Output as standard SRT format

To burn subtitles into video:
```bash
ffmpeg -i final_demo.mp4 -vf subtitles=demo.srt \
    -c:v libx264 -crf 18 -c:a copy \
    final_demo_subtitled.mp4
```

## Voice Configuration

Choose voice based on audience, use `eleven_turbo_v2` for drafts, `eleven_multilingual_v2` for final.

For voice IDs, settings guide, model comparison, and continuity chaining details, consult `references/elevenlabs-api.md`.

## Pacing Adjustments

| Problem | Solution | Limit |
|---------|----------|-------|
| Audio slightly too long | Speed up with `atempo` filter | Max 1.15x |
| Audio way too long | Shorten narration text, re-generate | Re-generate segment only |
| Audio too short | Add silence padding (natural) | Silence during demos is fine |
| Awkward gap between segments | Extend pause or add transition phrase | Keep pauses under 3s |

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
