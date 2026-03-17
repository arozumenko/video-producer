#!/usr/bin/env python3
"""Generate narration audio segments using ElevenLabs with-timestamps API.

Usage:
    python scripts/generate_narration.py --plan voiceover_plan.json --voice Rachel --output-dir .

Reads a voiceover plan JSON and produces per-segment MP3 files with alignment data.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys

import httpx

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

VOICE_IDS = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "adam": "pNInz6obpgDQGcFmaJgB",
    "bella": "EXAVITQu4vr4xnSDxMaL",
    "antoni": "ErXwobaYiN019PkySvjV",
}


async def generate_segment(
    text: str,
    index: int,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    previous_request_ids: list[str] | None = None,
    output_dir: str = ".",
) -> dict:
    """Generate one narration segment with character-level timestamps."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.80,
            "style": 0.15,
            "use_speaker_boost": True,
        },
        "output_format": "mp3_44100_128",
    }

    if previous_request_ids:
        payload["previous_request_ids"] = previous_request_ids[-3:]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"xi-api-key": ELEVENLABS_API_KEY},
        )
        response.raise_for_status()
        data = response.json()

    audio_bytes = base64.b64decode(data["audio_base64"])
    audio_path = os.path.join(output_dir, f"narration_{index:03d}.mp3")
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

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


async def generate_all(
    segments: list[dict], voice_id: str, model_id: str, output_dir: str
) -> list[dict]:
    """Generate all narration segments with cross-segment continuity."""
    results = []
    previous_request_ids: list[str] = []

    for seg in segments:
        result = await generate_segment(
            text=seg["text"],
            index=seg["index"],
            voice_id=voice_id,
            model_id=model_id,
            previous_request_ids=previous_request_ids or None,
            output_dir=output_dir,
        )
        results.append(result)

        if result["request_id"]:
            previous_request_ids.append(result["request_id"])
            previous_request_ids = previous_request_ids[-3:]

    return results


def main():
    parser = argparse.ArgumentParser(description="Generate narration segments via ElevenLabs")
    parser.add_argument("--plan", required=True, help="Path to voiceover plan JSON")
    parser.add_argument("--voice", default="rachel", help="Voice name (rachel, adam, bella, antoni)")
    parser.add_argument("--model", default="eleven_multilingual_v2", help="ElevenLabs model ID")
    parser.add_argument("--output-dir", default=".", help="Output directory for MP3 files")
    args = parser.parse_args()

    if not ELEVENLABS_API_KEY:
        print("Error: ELEVENLABS_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    voice_id = VOICE_IDS.get(args.voice.lower(), args.voice)

    with open(args.plan) as f:
        plan = json.load(f)

    segments = plan.get("segments", plan)

    results = asyncio.run(generate_all(segments, voice_id, args.model, args.output_dir))

    output_path = os.path.join(args.output_dir, "narration_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Generated {len(results)} segments -> {output_path}")


if __name__ == "__main__":
    main()
