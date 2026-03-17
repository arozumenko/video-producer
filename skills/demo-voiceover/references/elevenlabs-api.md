# ElevenLabs API Reference

## With-Timestamps Endpoint

```
POST https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps
Headers: xi-api-key: {API_KEY}
```

### Request Payload

```json
{
  "text": "Narration text here.",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.65,
    "similarity_boost": 0.80,
    "style": 0.15,
    "use_speaker_boost": true
  },
  "output_format": "mp3_44100_128",
  "previous_request_ids": ["abc123", "def456"]
}
```

### Response

```json
{
  "audio_base64": "...",
  "alignment": {
    "characters": ["H", "e", "l", "l", "o"],
    "character_start_times_seconds": [0.0, 0.05, 0.1, 0.15, 0.2],
    "character_end_times_seconds": [0.05, 0.1, 0.15, 0.2, 0.3]
  }
}
```

Response header `request-id` is used for continuity chaining.

## Continuity Chaining

Pass `previous_request_ids` (max 3) to make segments sound like one continuous narration:

```
Segment 1 → request_id: "abc123"
Segment 2 → previous_request_ids: ["abc123"], request_id: "def456"
Segment 3 → previous_request_ids: ["abc123", "def456"], request_id: "ghi789"
```

**Fallback** (re-generation without IDs): use `previous_text` / `next_text` fields.

## Voice IDs

| Voice | ID | Style |
|-------|----|-------|
| Rachel | 21m00Tcm4TlvDq8ikWAM | Professional, warm |
| Adam | pNInz6obpgDQGcFmaJgB | Clear, authoritative |
| Bella | EXAVITQu4vr4xnSDxMaL | Friendly, upbeat |
| Antoni | ErXwobaYiN019PkySvjV | Calm, measured |

## Voice Settings Guide

```
stability:        0.5-0.7 for demos (natural variation without instability)
similarity_boost: 0.75-0.85 (consistent voice character)
style:            0.10-0.20 (subtle expressiveness; higher = dramatic)
use_speaker_boost: true (always for demos — clarity enhancement)
```

## Model Selection

| Model | Speed | Quality | Languages | Cost |
|-------|-------|---------|-----------|------|
| `eleven_multilingual_v2` | Slower | Best | 29 | 1x |
| `eleven_turbo_v2` | Fast | Good | English only | 0.5x |
| `eleven_flash_v2_5` | Fastest | Good | Multilingual | 0.5x |

Use `eleven_turbo_v2` for drafts, `eleven_multilingual_v2` for final render.
