#!/usr/bin/env python3
"""
ascii_to_svg.py
----------------
Converts a photo into an animated ASCII-art SVG (wave / noise style),
similar to the popular "GitHub profile README" ASCII animations.

Usage:
    python3 ascii_to_svg.py profile.jpg --cols 70 --theme dark -o dark.svg
    python3 ascii_to_svg.py profile.jpg --cols 70 --theme light -o light.svg

Notes / design decisions:
- GitHub sanitizes README SVGs. <script> tags are stripped, but
  CSS <style> animations (@keyframes) survive and render correctly
  when the SVG is embedded via <img src="...svg">. So the animation
  here is pure CSS, not SMIL/JS.
- The "wave" effect is a traveling opacity/brightness pulse that
  sweeps left-to-right across the character grid, with a slight
  per-row time offset so it reads as a diagonal scan (matches the
  reference clip).
"""

import argparse
import numpy as np
from PIL import Image

# Character ramp from sparse -> dense. Index scales with brightness.
RAMP_DARKBG = " .:-=+*#%@"      # for dark background: bright pixel -> dense glyph
RAMP_LIGHTBG = "@%#*+=-:. "     # for light background: bright pixel -> sparse glyph

# Character cell aspect ratio correction (monospace glyphs are ~2x taller than wide)
CHAR_ASPECT = 0.55


def image_to_ascii_grid(path: str, cols: int) -> np.ndarray:
    """Load an image and reduce it to a 2D array of brightness values (0-1)."""
    img = Image.open(path).convert("L")  # grayscale
    w, h = img.size
    rows = max(1, int(cols * (h / w) * CHAR_ASPECT))
    img = img.resize((cols, rows))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr


def brightness_to_char(value: float, ramp: str) -> str:
    idx = int(value * (len(ramp) - 1))
    idx = max(0, min(len(ramp) - 1, idx))
    return ramp[idx]


def build_svg(grid: np.ndarray, theme: str, font_size: int = 9) -> str:
    rows, cols = grid.shape
    ramp = RAMP_DARKBG if theme == "dark" else RAMP_LIGHTBG

    # Colors tuned to look like the terminal/cyan aesthetic in the reference clip
    if theme == "dark":
        bg = "transparent"
        glyph_color = "#5ee6ff"
        glow_color = "#9be9ff"
    else:
        bg = "transparent"
        glyph_color = "#1b6a7a"
        glow_color = "#0d3d47"

    cell_w = font_size * CHAR_ASPECT
    cell_h = font_size
    svg_w = int(cols * cell_w) + 20
    svg_h = int(rows * cell_h) + 20

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}">'
    )
    lines.append(f'<rect width="100%" height="100%" fill="{bg}"/>')

    # CSS: a wave pulse that sweeps across columns, staggered per row for a diagonal feel
    lines.append("<style>")
    lines.append("text{font-family:'Courier New',monospace;dominant-baseline:middle;}")
    lines.append(
        "@keyframes wavepulse{{"
        "0%{{opacity:.25; fill:{0};}}"
        "50%{{opacity:1; fill:{1};}}"
        "100%{{opacity:.25; fill:{0};}}"
        "}}".format(glyph_color, glow_color)
    )
    for r in range(rows):
        delay = (r % 20) * 0.08
        lines.append(
            f".row{r}{{animation:wavepulse 3.2s ease-in-out {delay:.2f}s infinite;}}"
        )
    lines.append("</style>")

    for r in range(rows):
        y = 10 + r * cell_h + cell_h / 2
        chars = "".join(brightness_to_char(v, ramp) for v in grid[r])
        # Escape XML-sensitive characters
        chars = (
            chars.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        lines.append(
            f'<text class="row{r}" x="10" y="{y:.1f}" font-size="{font_size}" '
            f'fill="{glyph_color}" xml:space="preserve">{chars}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Convert a photo to an animated ASCII SVG")
    ap.add_argument("image", help="Path to source image (jpg/png)")
    ap.add_argument("--cols", type=int, default=70, help="Number of character columns")
    ap.add_argument("--theme", choices=["dark", "light"], default="dark")
    ap.add_argument("--font-size", type=int, default=9)
    ap.add_argument("-o", "--output", required=True, help="Output SVG path")
    args = ap.parse_args()

    grid = image_to_ascii_grid(args.image, args.cols)
    svg = build_svg(grid, args.theme, args.font_size)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {args.output} ({grid.shape[1]}x{grid.shape[0]} chars)")


if __name__ == "__main__":
    main()
