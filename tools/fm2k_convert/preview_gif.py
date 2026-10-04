"""Render a skill's image frames as an animated GIF, with a palette applied.

Walks the skill's blocks from the start and collects `I` (image) blocks until the
first `E` (end) or jump, ignoring every condition — good enough to eyeball an
animation, not an emulation. FM2K runs at 100 fps, so `wait` is in 10 ms units.

usage: preview_gif.py <asset dir> <skill number>... [--palette N] [--out DIR]
"""

import argparse
import json
import re
import struct
from pathlib import Path

from PIL import Image

BG = (96, 96, 112)


def load_json(stem, json_dir):
    return json.loads((json_dir / (stem + ".json")).read_text(encoding="utf-8-sig"))


def frames_of(skill):
    out = []
    for b in skill["blocks"]:
        if b["type"] == "I":
            out.append(b)
        elif b["type"] in ("E", "SG", "SC", "SF") and out:
            break
    return out


def image_path(asset_dir, i):
    """Image i's file, from images.lton (its folder, or assets/shared)."""
    entries = [ln for ln in (asset_dir / "images.lton").read_text(encoding="utf-8").splitlines()
               if ln.startswith("{") or ln.startswith("nil^")]
    m = re.search(r'(file|shared) = "([^"]+)"', entries[i])
    return asset_dir / m.group(2) if m.group(1) == "file" else asset_dir.parent.parent / "shared" / m.group(2)


def open_image(path):
    """A PNG, or convert.py's single-channel DDS (as an 8-bit grayscale image)."""
    if path.suffix == ".dds":
        from share_assets import dds_pixels
        w, h, pixels = dds_pixels(path.read_bytes())
        return Image.frombytes("L", (w, h), pixels)
    return Image.open(path)


def shade(path, palette, row):
    img = open_image(path)
    if img.mode == "L":
        p = Image.frombytes("P", img.size, img.tobytes())
        p.putpalette([c for i in range(256) for c in palette.getpixel((i, row))], rawmode="RGBA")
        return p.convert("RGBA")
    return img.convert("RGBA")


def render(asset_dir, d, number, row, out_dir):
    skill = d["skills"][number]
    frames = frames_of(skill)
    if not frames:
        return None
    palette = Image.open(asset_dir / "palettes.png").convert("RGBA")
    sprites = [(f, shade(image_path(asset_dir, f["i"]), palette, row)) for f in frames]
    # An I block's (x, y) is where the image's bottom-centre goes, relative to the
    # character origin (checked against the feet staying put in standing/walking).
    placed = [(f, s, f["x"] - s.width // 2, f["y"] - s.height) for f, s in sprites]
    left = min(px for _, _, px, _ in placed)
    top = min(py for _, _, _, py in placed)
    right = max(px + s.width for _, s, px, _ in placed)
    bottom = max(py + s.height for _, s, _, py in placed)
    size = (right - left + 20, bottom - top + 20)
    images, durations = [], []
    for f, s, px, py in placed:
        canvas = Image.new("RGBA", size, BG + (255,))
        canvas.alpha_composite(s, (px - left + 10, py - top + 10))
        images.append(canvas.convert("RGB"))
        durations.append(max(f["wait"], 1) * 10)
    out = out_dir / ("%s_%04d_%s_p%d.gif" % (asset_dir.name, number, skill["name"], row))
    images[0].save(out, save_all=True, append_images=images[1:], duration=durations, loop=0)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("asset_dir", type=Path)
    ap.add_argument("skills", type=int, nargs="+")
    ap.add_argument("--json-dir", type=Path, required=True, help="fm2ndparser JSON directory")
    ap.add_argument("--palette", type=int, nargs="+", default=[0])
    ap.add_argument("--out", type=Path, default=Path("assets/_preview"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    d = load_json(args.asset_dir.name, args.json_dir)
    for n in args.skills:
        for row in args.palette:
            print(render(args.asset_dir, d, n, row, args.out))


if __name__ == "__main__":
    main()
