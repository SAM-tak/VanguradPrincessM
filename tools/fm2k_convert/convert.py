"""Convert fm2ndparser JSON output into the port's native asset formats.

Input:  a directory of JSON files written by fm2ndparser (one per .kgt/.player/.stage/.demo).
Output: one directory per source file under OUT/<kind>/<name>/:

    data.lton       everything except images, sounds and skills
    images.lton     image list; position = original FM2K image number, nil^ = unused slot
    sounds.lton     sound list; position = original FM2K sound number, nil^ = unused slot
    skills/NNNN.lton  SKILLS_PER_FILE skills per file; `first` + position = skill number
    images/NNNN.dds indexed sprites: one 8-bit channel (value = palette index),
                    uncompressed DDS (8-bit luminance, L8), which LOVE loads as
                    an r8 texture (a PNG would decode to RGBA, four
                    times the memory; TechnicalDocuments/0021). Drawn through
                    palettes.png by a shader.
    images/NNNN.png sprites with their own palette, as RGBA.
    palettes.png    256 x 8 RGBA, one row per global palette (colour variant).
    sounds/NNNN.wav embedded sounds, byte-for-byte.

Pure black (RGB 0, 0, 0) is transparent everywhere (FM2K's colour key).

The LTON is split because lhat's compiler looks constants up linearly
(lhat_chunk_constant), so one big file compiles super-linearly, and a chunk is
capped at 65536 constants. Lists are written as positional elements rather than
`[n] = ...` keys: explicit integer keys compile about 5x slower.
"""

import argparse
import base64
import json
import math
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from layout import metadata_path

from PIL import Image

import patches
from names import UNUSED, official

KIND_DIRS = {"game": "system", "character": "characters", "stage": "stages", "demo": "demos"}
PALETTE_BYTES = 0x400

# Fields fm2ndparser emits that the port does not need: raw byte blobs whose
# meaning is only relevant to the original engine. (A skill's derived
# "settings" copy is dropped in slim_skill.)
DROP_KEYS = {"pointer", "data", "offset"}

# Per block type, fields fm2ndparser derives from other fields (see its json-spec.md).
DERIVED_BLOCK_KEYS = {
    "O": {"in", "depthEnabled"},
    "C": {"fails", "levelCancelCondition"},
    "M": {"replace"},
    "RC": {"out"},
    "RP": {"out"},
    "FD": {"damageRateEnabled"},
    "COLOR": {"aEnabled"},
}
SKILLS_PER_FILE = 100


# ---------------------------------------------------------------------------
# LTON writer

def lton_string(s):
    out = ['"']
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\0":
            out.append("\\0")
        elif ord(ch) < 0x20:
            out.append("\\u{%x}" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def is_identifier(key):
    return key.isascii() and key.replace("_", "a").isalnum() and not key[0].isdigit()


def lton_key(key):
    return key if is_identifier(key) else "[%s]" % lton_string(key)


def lton_scalar(v):
    if v is None:
        return "nil^"
    if v is True:
        return "true^"
    if v is False:
        return "false^"
    if isinstance(v, str):
        return lton_string(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise ValueError("non-finite number")
        return repr(v)
    return str(v)


def is_scalar(v):
    return not isinstance(v, (dict, list))


def lton_value(v, indent):
    if is_scalar(v):
        return lton_scalar(v)
    pad = "    " * (indent + 1)
    end = "    " * indent
    if isinstance(v, list):
        if not v:
            return "{}"
        if all(is_scalar(x) for x in v):
            return "{ " + ", ".join(lton_scalar(x) for x in v) + " }"
        return "{\n" + "".join(pad + lton_value(x, indent + 1) + ",\n" for x in v) + end + "}"
    items = [(k, x) for k, x in v.items() if x is not None]
    # A block's kind first: it is what one reads a block list by.
    items.sort(key=lambda kx: kx[0] != "type")
    if not items:
        return "{}"
    if all(is_scalar(x) for _, x in items) and len(items) <= 12:
        return "{ " + ", ".join("%s = %s" % (lton_key(k), lton_scalar(x)) for k, x in items) + " }"
    return "{\n" + "".join("%s%s = %s,\n" % (pad, lton_key(k), lton_value(x, indent + 1)) for k, x in items) + end + "}"


def write_lton(path, table, header, elements=()):
    """Named entries from `table`, then `elements` as positional entries (0-based;
    None is written as nil^, which keeps the numbering)."""
    lines = ["# " + line for line in header]
    for k, v in table.items():
        if v is not None:
            lines.append("%s = %s," % (lton_key(k), lton_value(v, 0)))
    for v in elements:
        lines.append("%s," % lton_value(v, 0))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def strip(v):
    if isinstance(v, dict):
        return {k: strip(x) for k, x in v.items() if k not in DROP_KEYS}
    if isinstance(v, list):
        return [strip(x) for x in v]
    return v


# ---------------------------------------------------------------------------
# media

def palette_rgba(raw):
    """FM2K palette bytes (BGRx per entry) -> 256 RGBA tuples.

    FM2K keys out pure black: entries of RGB (0, 0, 0) are transparent, and art
    that means black uses a near-black such as (8, 0, 0). In characters' palettes
    that entry is index 0; stage images put it anywhere."""
    cols = []
    for i in range(256):
        b, g, r = raw[i * 4], raw[i * 4 + 1], raw[i * 4 + 2]
        cols.append((r, g, b, 0 if (r, g, b) == (0, 0, 0) else 255))
    return cols


def write_palettes(path, global_palettes):
    img = Image.new("RGBA", (256, len(global_palettes)))
    for row, pal in enumerate(global_palettes):
        for i, c in enumerate(palette_rgba(base64.b64decode(pal["data"]))):
            img.putpixel((i, row), c)
    img.save(path, optimize=True)


def image_name(i, fmt):
    return "images/%04d.%s" % (i, "dds" if fmt == "indexed" else "png")


def dds_l8_header(w, h):
    """An uncompressed 8-bit luminance DDS header (the classic L8 layout, which
    image viewers read; LOVE takes it as R8_UNORM). The DX10 header with DXGI
    R8_UNORM loads the same in LOVE, but viewers and Pillow refuse it."""
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000           # caps, height, width, pitch, pixel format
    pixel_format = struct.pack("<II4sIIIII", 32, 0x20000, bytes(4), 8, 0xFF, 0, 0, 0)  # luminance, 8 bits, R mask
    return (b"DDS " + struct.pack("<IIIIIII", 124, flags, h, w, w, 0, 1) + bytes(44) + pixel_format
            + struct.pack("<IIIII", 0x1000, 0, 0, 0, 0))   # caps: texture


def write_dds_r8(path, w, h, pixels):
    """An uncompressed single-channel DDS (L8; loaded as an r8 texture)."""
    path.write_bytes(dds_l8_header(w, h) + bytes(pixels))


def write_image(path, im):
    w, h = im["width"], im["height"]
    raw = base64.b64decode(im["data"])
    if im["paletteType"] == 1:
        img = Image.frombytes("P", (w, h), raw[PALETTE_BYTES:PALETTE_BYTES + w * h])
        img.putpalette([c for rgba in palette_rgba(raw[:PALETTE_BYTES]) for c in rgba], rawmode="RGBA")
        img.convert("RGBA").save(path, optimize=True)
        return "rgba"
    write_dds_r8(path, w, h, raw[:w * h])
    return "indexed"


# ---------------------------------------------------------------------------

def classify(files):
    """Map JSON stem -> kind, using the lists inside the .kgt JSON (the parser's own
    "type" field holds the file signature, not the kind)."""
    kinds = {}
    for f in files:
        with f.open(encoding="utf-8-sig") as fp:
            head = fp.read(4096)
        if '"characters"' not in head:
            continue
        g = json.loads(f.read_text(encoding="utf-8-sig"))
        kinds[f.stem] = "game"
        for key, kind in (("characters", "character"), ("stages", "stage"), ("demos", "demo")):
            for name in g[key]:
                kinds.setdefault(name, kind)
    return kinds


def slim_skill(skill):
    blocks = []
    for b in skill["blocks"]:
        drop = DERIVED_BLOCK_KEYS.get(b["type"], set()) | {"index"}
        blocks.append({k: v for k, v in b.items() if k not in drop})
    return {"name": skill["name"], "type": skill["type"], "blocks": blocks}


def convert(src, out_root, kind, media=True):
    d = json.loads(src.read_text(encoding="utf-8-sig"))
    patches.apply(src, d)           # the port's deliberate changes (patches/)
    if kind == "game":              # the character list under the port's names (names.py)
        d["characters"] = [official(n) for n in d["characters"]]
    dst = out_root / KIND_DIRS[kind] / official(src.stem)
    (dst / "images").mkdir(parents=True, exist_ok=True)
    definitions = metadata_path(dst)
    definitions.mkdir(parents=True, exist_ok=True)
    header = ["Converted from %s by tools/fm2k_convert/convert.py" % src.name]

    images = []
    for i, im in enumerate(d.pop("images")):
        if not im["width"] or not im["height"] or not im.get("data"):
            continue
        fmt = "rgba" if im["paletteType"] == 1 else "indexed"
        name = image_name(i, fmt)
        if media:
            write_image(dst / name, im)
        images.append((i, {"file": name, "width": im["width"], "height": im["height"], "format": fmt}))

    sounds = []
    snd = d.pop("sounds")
    if any(s.get("data") for s in snd):
        (dst / "sounds").mkdir(exist_ok=True)
    for i, s in enumerate(snd):
        entry = {"name": s["name"], "type": s["type"], "endlessLoop": s["endlessLoop"], "cddaTrack": s["cddaTrack"]}
        if s.get("data"):
            entry["file"] = "sounds/%04d.wav" % i
            if media:
                (dst / entry["file"]).write_bytes(base64.b64decode(s["data"]))
        if s["name"] or "file" in entry:
            sounds.append((i, entry))

    palettes = d.pop("globalPalettes")
    if media and any(x["format"] == "indexed" for _, x in images):
        write_palettes(dst / "palettes.png", palettes)

    def numbered(pairs):
        out = [None] * (max((i for i, _ in pairs), default=-1) + 1)
        for i, x in pairs:
            out[i] = x
        return out

    write_lton(definitions / "images.lton", {}, header + ["Position = original FM2K image number; nil^ = unused slot."], numbered(images))
    write_lton(definitions / "sounds.lton", {}, header + ["Position = original FM2K sound number; nil^ = unused slot."], numbered(sounds))

    skills = d.pop("skills")
    skill_dir = dst / "skills"
    skill_dir.mkdir(exist_ok=True)
    for old in skill_dir.glob("*.lton"):
        old.unlink()
    for first in range(0, len(skills), SKILLS_PER_FILE):
        chunk = [slim_skill(x) for x in skills[first:first + SKILLS_PER_FILE]]
        write_lton(skill_dir / ("%04d.lton" % first), {"first": first},
                   header + ["Skill number (SkillReference.number) = first + position."], chunk)

    d.pop("type")
    table = {"kind": kind, "name": d.pop("name"), "skillCount": len(skills), "skillsPerFile": SKILLS_PER_FILE}
    table.update(strip(d))
    write_lton(definitions / "data.lton", table, header)
    images = [x for _, x in images]
    return "%s: %d images, %d sounds -> %s" % (src.name, len(images), len(sounds), dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_dir", type=Path, help="directory of fm2ndparser JSON files")
    ap.add_argument("out", type=Path, help="output root (e.g. assets)")
    ap.add_argument("--only", nargs="*", help="convert only these JSON stems")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--lton-only", action="store_true", help="rewrite the LTON only, leave png/wav alone")
    args = ap.parse_args()

    files = sorted(args.json_dir.glob("*.json"))
    kinds = classify(files)
    skipped = [f.name for f in files if f.stem not in kinds]
    if skipped:
        print("not referenced by the .kgt, skipped:", ", ".join(skipped))
    unused = [f.name for f in files if f.stem in UNUSED]
    if unused:
        print("unused characters, skipped:", ", ".join(unused))
    files = [f for f in files if f.stem in kinds and f.stem not in UNUSED]
    if args.only:
        files = [f for f in files if f.stem in args.only]
    if not files:
        sys.exit("no JSON files found")

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for msg in ex.map(convert, files, [args.out] * len(files), [kinds[f.stem] for f in files],
                          [not args.lton_only] * len(files)):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
