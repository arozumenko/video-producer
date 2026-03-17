# Video Producer

AI-powered product demo video production pipeline using Claude Code agents and skills.

## Project Structure

```
video-producer/
├── agents/
│   └── video-producer/        ← orchestrator agent (full pipeline)
├── skills/
│   ├── demo-script/           ← co-author structured demo scripts
│   ├── record-demo/           ← record browser demos (Playwright + ffmpeg)
│   └── demo-voiceover/        ← generate & sync ElevenLabs narration
├── workspace/                 ← output directory (git-ignored)
├── CLAUDE.md
└── README.md
```

## Pipeline

```
/demo-script  →  /record-demo  →  /demo-voiceover
  (plan)          (capture)         (narrate & deliver)
```

The `video-producer` agent orchestrates all three skills end-to-end.

## Dependencies

- **ffmpeg** (with avfoundation on macOS, libx264, aac)
- **Playwright** (`pip install playwright && playwright install chromium`)
- **ElevenLabs** API key (`ELEVENLABS_API_KEY` env var)
- **Playwright MCP server** (for browser tools: navigate, screenshot, click, type)

## Workspace

All output goes to `workspace/<date>/`. This directory is git-ignored.

## Conventions

- Workspace path is `workspace/<date>/` (NOT `.octo/workspace/`)
- Skills are standalone — each can be invoked independently via `/skill-name`
- The agent uses Playwright MCP tools for browser interaction (headful mode for recording)
- Voice-over uses ElevenLabs with-timestamps API for character-level alignment
- ffmpeg avfoundation for macOS screen capture (not Playwright recordVideo)

## Production Notes (macOS)

- Screen Recording permission required for ffmpeg (System Settings → Privacy & Security)
- Multi-monitor: use `system_profiler SPDisplaysDataType` to detect displays
- ffmpeg device listing: `ffmpeg -f avfoundation -list_devices true -i ""`
- Retina displays: ffmpeg captures at physical resolution, scale down for 1080p output
