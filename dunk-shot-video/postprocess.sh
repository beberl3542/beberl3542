#!/usr/bin/env bash
# Turn a raw generated clip into 3840x2160 @ 60fps, 4 seconds.
#
#   ./postprocess.sh out/raw.mp4 [out/dunk_4k60.mp4] [start_seconds]
#
# Uses RIFE (rife-ncnn-vulkan) and Real-ESRGAN (realesrgan-ncnn-vulkan) when
# they are on PATH, otherwise falls back to ffmpeg-only motion interpolation
# and lanczos scaling. Requires ffmpeg + ffprobe.
set -euo pipefail

IN=${1:?input video}
OUT=${2:-$(dirname "$IN")/dunk_4k60.mp4}
START=${3:-0}
DUR=4
FPS=60
W=3840; H=2160

for t in ffmpeg ffprobe; do command -v "$t" >/dev/null || { echo "missing $t" >&2; exit 1; }; done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/dunkpp.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

echo "[1/4] trim -> ${DUR}s from ${START}s"
ffmpeg -v error -y -ss "$START" -i "$IN" -t "$DUR" -an -c:v libx264 -crf 10 -preset fast "$WORK/trim.mp4"

SRC_FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$WORK/trim.mp4")

if command -v rife-ncnn-vulkan >/dev/null; then
  echo "[2/4] interpolate -> ${FPS}fps (RIFE)"
  mkdir -p "$WORK/in" "$WORK/i60"
  ffmpeg -v error -i "$WORK/trim.mp4" "$WORK/in/%06d.png"
  N_IN=$(ls "$WORK/in" | wc -l)
  N_OUT=$(python3 -c "from fractions import Fraction as F;print(round($N_IN*$FPS/F('$SRC_FPS')))")
  rife-ncnn-vulkan -i "$WORK/in" -o "$WORK/i60" -n "$N_OUT" -m rife-v4.6 >/dev/null
  ffmpeg -v error -y -framerate "$FPS" -i "$WORK/i60/%08d.png" -c:v libx264 -crf 10 -preset fast -pix_fmt yuv420p "$WORK/fps60.mp4"
else
  echo "[2/4] interpolate -> ${FPS}fps (ffmpeg minterpolate; install rife-ncnn-vulkan for better quality)"
  ffmpeg -v error -y -i "$WORK/trim.mp4" \
    -vf "minterpolate=fps=${FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" \
    -c:v libx264 -crf 10 -preset fast "$WORK/fps60.mp4"
fi

if command -v realesrgan-ncnn-vulkan >/dev/null; then
  echo "[3/4] upscale -> ${W}x${H} (Real-ESRGAN)"
  mkdir -p "$WORK/f60" "$WORK/f4k"
  ffmpeg -v error -i "$WORK/fps60.mp4" "$WORK/f60/%08d.png"
  realesrgan-ncnn-vulkan -i "$WORK/f60" -o "$WORK/f4k" -n realesrgan-x4plus -s 4 >/dev/null
  UP_IN="-framerate $FPS -i $WORK/f4k/%08d.png"
else
  echo "[3/4] upscale -> ${W}x${H} (ffmpeg lanczos; install realesrgan-ncnn-vulkan for better quality)"
  UP_IN="-i $WORK/fps60.mp4"
fi

echo "[4/4] encode -> $OUT"
mkdir -p "$(dirname "$OUT")"
# shellcheck disable=SC2086
ffmpeg -v error -y $UP_IN \
  -vf "scale=${W}:${H}:flags=lanczos,format=yuv420p" \
  -r "$FPS" -c:v libx264 -crf 16 -preset slow -movflags +faststart -an "$OUT"

echo
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate:format=duration -of default=noprint_wrappers=1 "$OUT"
