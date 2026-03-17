#!/usr/bin/env bash
# Merge narration audio segments with raw video using ffmpeg.
#
# Usage:
#   bash scripts/merge_audio_video.sh <video.mp4> <narration_results.json> <output.mp4>
#
# Reads narration_results.json (from generate_narration.py) to get segment paths
# and timing, then builds an ffmpeg filter_complex to place each segment at the
# correct timestamp.

set -euo pipefail

VIDEO="$1"
RESULTS="$2"
OUTPUT="$3"

if [ ! -f "$VIDEO" ] || [ ! -f "$RESULTS" ]; then
    echo "Usage: $0 <video.mp4> <narration_results.json> <output.mp4>" >&2
    exit 1
fi

# Build ffmpeg command from narration results
python3 -c "
import json, sys

with open('$RESULTS') as f:
    results = json.load(f)

inputs = ['-i \"$VIDEO\"']
filters = []
streams = []

for i, r in enumerate(results):
    inputs.append(f'-i \"{r[\"audio_path\"]}\"')
    delay_ms = int(r.get('video_start_sec', i * 5) * 1000)
    speed = r.get('speed_factor', 1.0)
    label = f'a{i}'
    if speed != 1.0:
        filters.append(f'[{i+1}]atempo={speed:.3f},adelay={delay_ms}|{delay_ms}[{label}]')
    else:
        filters.append(f'[{i+1}]adelay={delay_ms}|{delay_ms}[{label}]')
    streams.append(f'[{label}]')

n = len(streams)
mix = ''.join(streams)
filters.append(f'{mix}amix=inputs={n}:duration=longest:normalize=0[narration]')

cmd = f'ffmpeg {\" \".join(inputs)} -filter_complex \"{\";\".join(filters)}\" -map 0:v -map \"[narration]\" -c:v copy -c:a aac -b:a 192k -shortest \"$OUTPUT\"'
print(cmd)
" | bash

echo "Merged -> $OUTPUT"
