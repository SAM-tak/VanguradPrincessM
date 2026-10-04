"""Finds the images and sounds the characters hold in common (the same bytes in
two or more characters' folders: the supports, common effects, ...).

    share_assets.py <assets dir> --apply

moves every content held by two or more characters (or already in the pool)
to assets/shared/images|sounds/<key>.dds|png|wav (key: content_key), deletes the characters' copies
and points their images.lton / sounds.lton entries at it: `file =
"images/NNNN.dds"` becomes `shared = "images/<key>.dds"` (src/sprite.lh's
assetPath; TechnicalDocuments/0020). The skills keep their own numbers. Run it
after convert.py; it can run again (a character converted anew joins the pool).

Images listed in share_owners.txt are one character's own, held by others by
mistake: they stay in the owner's folder, and the others' entries become nil^.

    share_assets.py <assets dir> --preview <dir>

writes the split for looking at instead, and leaves the assets alone:

    <dir>/shared/images/kNN/<hash>__<char>-<number>+....png   held by NN characters
    <dir>/shared/sounds/kNN/...wav
    <dir>/own/<char>/images/<number>.png                       only that character's
    <dir>/own/<char>/sounds/<number>.wav
    <dir>/report.txt                                           counts and sizes

"""

import argparse
import collections
import hashlib
import re
import shutil
import struct
from pathlib import Path

KINDS = (("images", ("dds", "png")), ("sounds", ("wav",)))


def dds_pixels(b):
    """A single-channel DDS's (width, height, pixels): convert.py's L8, or the
    DX10 header form it wrote before."""
    h, w = struct.unpack("<II", b[12:20])
    start = 4 + 124 + (20 if b[84:88] == b"DX10" else 0)
    return w, h, b[start:start + w * h]


def content_key(f):
    """What two files must share to be the same asset. A sound: its bytes. An
    image: its size, mode and pixels, so the same picture matches whether it
    is a PNG or a DDS (share_owners.txt is keyed by this)."""
    if f.suffix == ".wav":
        return hashlib.sha1(f.read_bytes()).hexdigest()
    if f.suffix == ".dds":
        w, h, pixels = dds_pixels(f.read_bytes())
        head = ("%dx%d:L:" % (w, h)).encode()
    else:
        from PIL import Image
        im = Image.open(f)
        head, pixels = ("%dx%d:%s:" % (im.width, im.height, im.mode)).encode(), im.tobytes()
    return hashlib.sha1(head + pixels).hexdigest()


def scan(assets):
    """{kind: {key: [(character, number, path)]}} over every character's folder."""
    found = {kind: collections.defaultdict(list) for kind, _ in KINDS}
    for char_dir in sorted((assets / "characters").iterdir()):
        if not char_dir.is_dir():
            continue
        for kind, exts in KINDS:
            for ext in exts:
                for f in sorted((char_dir / kind).glob("*." + ext)):
                    found[kind][content_key(f)].append((char_dir.name, int(f.stem), f))
    return found


def preview(found, out):
    if out.exists():
        shutil.rmtree(out)
    lines = []
    for kind, _ in KINDS:
        by_hash = found[kind]
        shared = {h: v for h, v in by_hash.items() if len({c for c, _, _ in v}) > 1}
        own = {h: v for h, v in by_hash.items() if h not in shared}
        size = lambda groups: sum(v[0][2].stat().st_size for v in groups.values())
        total = sum(f.stat().st_size for v in by_hash.values() for _, _, f in v)
        lines.append("%s: %d files, %.1f MB" % (kind, sum(len(v) for v in by_hash.values()), total / 1e6))
        lines.append("  shared: %d contents (%.1f MB once) in %d files"
                     % (len(shared), size(shared) / 1e6, sum(len(v) for v in shared.values())))
        lines.append("  own:    %d contents (%.1f MB)" % (len(own), size(own) / 1e6))
        lines.append("  after:  %.1f MB" % ((size(shared) + size(own)) / 1e6))
        hist = collections.Counter(len({c for c, _, _ in v}) for v in shared.values())
        lines.append("  shared by k characters: " + ", ".join("%d: %d" % (k, hist[k]) for k in sorted(hist)))
        per_char = collections.Counter(c for v in own.values() for c, _, _ in v)
        lines.append("  own per character: " + ", ".join("%s %d" % kv for kv in sorted(per_char.items())))

        for h, v in shared.items():
            k = len({c for c, _, _ in v})
            where = "+".join("%s-%04d" % (c, n) for c, n, _ in v)
            dst = out / "shared" / kind / ("k%02d" % k) / ("%s__%s%s" % (h[:8], where[:120], v[0][2].suffix))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(v[0][2], dst)
        for v in own.values():
            for c, n, f in v:
                dst = out / "own" / c / kind / f.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dst)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


OWNERS = Path(__file__).with_name("share_owners.txt")


def owners():
    """{sha1 prefix: character} from share_owners.txt: held by several, but one's own."""
    out = {}
    for line in OWNERS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].split()
        if len(line) == 2:
            out[line[0]] = line[1]
    return out


def owner_of(h, table):
    for prefix, c in table.items():
        if h.startswith(prefix):
            return c
    return None


def rewrite_listing(listing, kind, shared, dropped):
    """Points the listing's entries at the pool (shared: {number: pool file})
    and empties the dropped numbers' entries (nil^, as an unused number)."""
    entry = re.compile(r'file = "%s/(\d+)\.\w+"' % kind)
    out = []
    for line in listing.read_text(encoding="utf-8").splitlines():
        m = entry.search(line)
        if m:
            n = int(m.group(1))
            if n in dropped:
                line = "nil^,"
            elif n in shared:
                line = line[:m.start()] + 'shared = "%s/%s"' % (kind, shared[n]) + line[m.end():]
        out.append(line)
    listing.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def apply(assets, found):
    pool = assets / "shared"
    table = owners()
    lines = []
    for kind, _ in KINDS:
        have = {f.stem for f in (pool / kind).glob("*")} if (pool / kind).exists() else set()
        shared = collections.defaultdict(dict)       # character -> {number: hash}
        dropped = collections.defaultdict(set)       # character -> numbers: another's image
        contents = 0
        for h, v in found[kind].items():
            if len({c for c, _, _ in v}) < 2 and h not in have:
                continue
            owner = owner_of(h, table)
            if owner is not None:
                for c, n, _ in v:
                    if c != owner:
                        dropped[c].add(n)
                continue
            dst = pool / kind / (h + v[0][2].suffix)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(v[0][2], dst)
            contents += 1
            for c, n, _ in v:
                shared[c][n] = dst.name
        files = {(c, n): f for v in found[kind].values() for c, n, f in v}
        for c in set(shared) | set(dropped):
            rewrite_listing(assets / "characters" / c / ("%s.lton" % kind), kind, shared[c], dropped[c])
            for n in set(shared[c]) | dropped[c]:
                files[(c, n)].unlink()
        lines.append("%s: %d contents in assets/shared, %d characters' copies removed, %d entries of another's image dropped"
                     % (kind, contents, sum(len(ns) for ns in shared.values()), sum(len(ns) for ns in dropped.values())))
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("assets", type=Path)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="move the shared files and rewrite the listings")
    mode.add_argument("--preview", type=Path, help="write the split here instead, for looking at")
    args = ap.parse_args()
    found = scan(args.assets)
    if args.preview:
        preview(found, args.preview)
    else:
        apply(args.assets, found)


if __name__ == "__main__":
    main()
