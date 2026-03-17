# Video Producer

AI-powered product demo video production pipeline for Claude Code. Automates the entire workflow from scripting to recording to voice-over narration.

## What It Does

Create professional product demo videos by describing what you want to show. The pipeline handles:

1. **Scripting** — Explores the live product, co-authors a structured recording script with actions, narration, and timing
2. **Recording** — Automates browser interaction via Playwright, captures high-quality H.264 video via ffmpeg
3. **Voice-Over** — Generates synchronized AI narration using ElevenLabs TTS with character-level timing

## Quick Start

### Prerequisites

- [Claude Code](https://claude.ai/claude-code) CLI
- ffmpeg (`brew install ffmpeg`)
- Playwright (`pip install playwright && playwright install chromium`)
- ElevenLabs API key

### Setup

```bash
# Clone into your workspace
git clone https://github.com/elitea-ai/video-producer.git

# Set your ElevenLabs API key
export ELEVENLABS_API_KEY="your-key-here"

# Ensure Playwright MCP server is configured in your .mcp.json
```

### Usage

Open Claude Code in this directory and use the agent or individual skills:

```
# Full pipeline — agent guides you through everything
@video-producer Create a demo of the login flow on staging.example.com

# Individual skills
/demo-script    — Write a demo script by exploring the live product
/record-demo    — Record a demo video from an approved script
/demo-voiceover — Add voice-over narration to a recorded demo
```

## Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ /demo-script │───▶│ /record-demo │───▶│/demo-voiceover│
│  (plan)      │    │  (capture)   │    │ (narrate)     │
└─────────────┘    └──────────────┘    └─────────────┘
```

Each skill can also be used independently.

## Output

Videos are saved to `workspace/<date>/`:

| File | Description |
|------|-------------|
| `<name>_final.mp4` | Video + narration |
| `<name>_final_subtitled.mp4` | Video + narration + burned-in subtitles |
| `<name>.srt` | Subtitle file |
| `<name>_script.json` | Machine-readable script (for re-recording) |
| `<name>_script.md` | Human-readable script |

## Architecture

- **Agent** (`.claude/agents/video-producer/`) — Orchestrator with creative decision-making. Manages discovery, exploration, scripting, recording, voice-over, and iteration.
- **Skills** (`skills/`) — Three focused skills that handle scripting, recording, and narration respectively.
- **Browser Tools** — Playwright MCP server provides `browser_navigate`, `browser_click`, `browser_type`, `browser_take_screenshot`, `browser_snapshot` for product exploration and recording.
- **Video Capture** — Hybrid approach: Playwright headful mode for browser automation + ffmpeg avfoundation for high-quality screen capture.
- **Voice-Over** — ElevenLabs with-timestamps API for character-level alignment, continuity chaining across segments, and automatic subtitle generation.

## Voice Options

| Voice | Style | Best for |
|-------|-------|----------|
| Rachel | Professional, warm | Product demos, marketing |
| Adam | Clear, authoritative | Technical walkthroughs |
| Bella | Friendly, upbeat | Onboarding tutorials |
| Antoni | Calm, measured | Enterprise demos |

## License

MIT
