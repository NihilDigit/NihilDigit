#!/usr/bin/env bash
# Rasterize every SVG card in the given directory to a 2x AVIF next to it.
#
# The cards rely on CSS animations with fill-mode forwards for their final
# state (text starts at opacity 0, the rank ring is drawn by keyframes), and
# disable_animations only zeroes the duration. Static renderers such as
# rsvg-convert ignore CSS animations and output blank cards, so a headless
# browser does the rendering.
set -euo pipefail

cd "$1"

for svg in *.svg; do
  name="${svg%.svg}"
  width=$(grep -m1 -oP 'width="\K\d+' "$svg")
  height=$(grep -m1 -oP 'height="\K\d+' "$svg")

  google-chrome --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --default-background-color=00000000 \
    --window-size="$width,$height" --screenshot="$PWD/$name.png" \
    "file://$PWD/$svg"

  # 4:4:4 keeps colored text and thin icon strokes free of chroma bleeding
  avifenc --qcolor 80 --yuv 444 --speed 4 "$name.png" "$name.avif"
  rm "$name.png" "$svg"
done
