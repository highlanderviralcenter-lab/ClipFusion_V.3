#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 5 ]; then
  echo "uso: $0 <input> <start> <duration> <srt> <output>"
  exit 1
fi
IN="$1"; START="$2"; DUR="$3"; SRT="$4"; OUT="$5"
TMP=$(mktemp /tmp/clipfusion_raw_XXXX.mp4)

# Passo 1: VA-API (proteção/escala)
ffmpeg -y -hwaccel vaapi -hwaccel_device /dev/dri/renderD128 \
  -ss "$START" -i "$IN" -t "$DUR" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=nv12,hwupload,scale_vaapi=1080:1920" \
  -c:v h264_vaapi -c:a aac -b:a 128k -map_metadata -1 "$TMP"

# Passo 2: libx264 (legendas/finalização)
nice -n -5 ffmpeg -y -i "$TMP" \
  -vf "subtitles='${SRT//:/\\:}'" \
  -c:v libx264 -preset fast -crf 21 -c:a copy -pix_fmt yuv420p -movflags +faststart "$OUT"
rm -f "$TMP"
