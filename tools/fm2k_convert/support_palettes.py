"""Deduplicate support index images with independently verified palette banks.

Run after media ownership organization. Default is a read-only audit.
Only exact index-renaming equivalence is accepted; dimensions stay unchanged.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from PIL import Image
from layout import metadata_path, media_path
from organize_support_media import REF, resolve
from share_assets import dds_pixels


def pattern(pixels):
    """Canonical partition of pixels, independent of the original index values."""
    mapping = {}
    for value in pixels:
        if value not in mapping:
            mapping[value] = len(mapping)
    return pixels.translate(bytes(mapping.get(i, 0) for i in range(256)))


def index_pairs(original, canonical):
    mapping = {a: canonical[original.index(a)] for a in set(original)}
    if original.translate(bytes(mapping.get(i, 0) for i in range(256))) != canonical:
        raise ValueError('Not an exact index renaming')
    return mapping.items()


def requirements(original, canonical, palette):
    result = {}
    for a, b in index_pairs(original, canonical):
        colors = tuple(palette[row * 256 + a] for row in range(8))
        if b in result and result[b] != colors:
            raise ValueError('Conflicting colors in an index mapping')
        result[b] = colors
    return result


def compatible(bank, colors):
    return all(index not in bank or bank[index] == value for index, value in colors.items())


def run(root, support, apply=False):
    root = root.resolve()
    folder = root / 'supports' / support / 'images'
    images, groups = {}, defaultdict(list)
    for path in sorted(folder.glob('*.dds'), key=lambda p: (not p.stem.isdigit(), p.name)):
        w, h, pixels = dds_pixels(path.read_bytes())
        if len(pixels) != w * h:
            raise ValueError(f'Truncated image: {path}')
        images[path] = (w, h, pixels)
        groups[w, h, pattern(pixels)].append(path)
    representatives = {p: paths[0] for paths in groups.values() for p in paths}
    changes, banks, references = {}, defaultdict(list), []
    palette_cache = {}
    for listing in sorted(metadata_path(root).rglob('images.lton')):
        if '_conversion' in listing.parts:
            continue
        lines = listing.read_text(encoding='utf-8').splitlines()
        for n, line in enumerate(lines):
            path = resolve(root, listing, line)
            if path not in images or 'format = "indexed"' not in line:
                continue
            existing = re.search(r'\bpalette = "([^"]+)"', line)
            pal_path = root.parent / existing[1] if existing else media_path(listing.parent) / 'palettes.png'
            if pal_path not in palette_cache:
                with Image.open(pal_path) as pal:
                    if pal.size != (256, 8):
                        raise ValueError(f'Unexpected palette size: {pal_path}')
                    raw = pal.convert('RGBA').tobytes()
                    palette_cache[pal_path] = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
            canonical = representatives[path]
            source = images[path][2]
            target = images[canonical][2]
            colors = requirements(source, target, palette_cache[pal_path])
            # Pack compatible mappings into one bank per owner where possible.
            owner = listing.parent.name
            bank = next((b for b in banks[owner] if compatible(b, colors)), None)
            if bank is None:
                bank = {}
                banks[owner].append(bank)
            bank.update(colors)
            references.append((listing, n, line, path, canonical, bank, pal_path))
            changes[listing] = lines
    generated = {}
    bank_paths = {}
    for owner, items in banks.items():
        for bank in items:
            raw = bytes(c for row in range(8) for index in range(256)
                        for c in bank.get(index, ((0, 0, 0, 0),) * 8)[row])
            digest = hashlib.sha256(raw).hexdigest()[:16]
            path = metadata_path(root) / 'supports' / support / 'palettes' / f'{owner}-{digest}.png'
            generated[path] = raw
            bank_paths[id(bank)] = path
    for listing, n, line, source, canonical, bank, pal_path in references:
        # Verify every pixel under all eight palettes, including hidden RGB.
        expected = palette_cache[pal_path]
        for a, b in index_pairs(images[source][2], images[canonical][2]):
            for row in range(8):
                if expected[row * 256 + a] != bank[b][row]:
                    raise AssertionError(f'RGBA mismatch: {listing}:{n}, row {row}')
        asset = 'assets/' + canonical.relative_to(root).as_posix()
        palette = bank_paths[id(bank)].relative_to(root.parent).as_posix()
        line = REF.sub(lambda _: f'asset = "{asset}"', line, count=1)
        line = re.sub(r',?\s*palette = "[^"]+"', '', line)
        changes[listing][n] = line.replace('format = "indexed"', f'format = "indexed", palette = "{palette}"')
    # Preserve files referenced by conversion intermediates and unrelated manifests.
    used = set()
    for listing in metadata_path(root).rglob('images.lton'):
        lines = changes.get(listing, listing.read_text(encoding='utf-8').splitlines())
        used.update(resolve(root, listing, line) for line in lines)
    removed = [p for p in images if p not in used and representatives[p] != p]
    report = dict(images=len(images), unique_patterns=len(groups), references=len(references),
                  palettes={owner: len(items) for owner, items in banks.items()},
                  removable_images=len(removed), removed_bytes=sum(p.stat().st_size for p in removed))
    if apply:
        # Verify encoded palette files before switching any manifests.
        for path, raw in generated.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.frombytes('RGBA', (256, 8), raw).save(path)
            with Image.open(path) as image:
                assert image.convert('RGBA').tobytes() == raw
        for listing, lines in changes.items():
            listing.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        for path in removed:
            path.unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--support', default='えこ')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.assets, args.support, args.apply), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
