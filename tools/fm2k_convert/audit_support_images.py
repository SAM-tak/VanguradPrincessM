"""Read-only comparison of explicitly owned support variants with numbered media.

Compare decoded indices first, then visible RGBA under every referring owner's
8 palette rows. Similarity alone never authorizes a replacement or deletion.
Requires Pillow (the converter's existing dependency).
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from PIL import Image
from organize_support_media import entries, explicit_owners, resolve
from layout import metadata_path
from share_assets import dds_pixels


def pixels(path):
    if path.suffix == '.dds':
        w, h, data = dds_pixels(path.read_bytes())
        return (w, h, 'L'), data
    with Image.open(path) as image:
        return (image.width, image.height, image.mode), image.tobytes()


def audit(root, support):
    root = root.resolve()
    selected = {f for f, owner in explicit_owners().items() if owner == support}
    refs, uses, body_uses = defaultdict(list), defaultdict(list), defaultdict(list)
    palettes = {}
    for listing in sorted((metadata_path(root) / 'characters').glob('*/images.lton')):
        owner = listing.parent.name
        script = metadata_path(root) / 'supports' / support / (owner + '.lton')
        used = set(map(int, re.findall(r'\{ "I", (\d+),', script.read_text(encoding='utf-8')))) if script.exists() else set()
        body = listing.with_name('script.lton')
        body_used = set(map(int, re.findall(r'\{ "I", (\d+),', body.read_text(encoding='utf-8')))) if body.exists() else set()
        for n, line in enumerate(entries(listing)):
            path = resolve(root, listing, line)
            if path and path.name in selected:
                refs[path.name].append([owner, n])
                if n in used:
                    uses[path.name].append([owner, n])
                if n in body_used:
                    body_uses[path.name].append([owner, n])
        palette = root / 'characters' / owner / 'palettes.png'
        if palette.exists():
            with Image.open(palette) as image:
                if image.size != (256, 8):
                    raise ValueError(f'Unexpected palette dimensions: {palette}')
                raw = image.convert('RGBA').tobytes()
                palettes[owner] = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    folder = root / 'supports' / support / 'images'
    existing = {p: pixels(p) for p in folder.iterdir() if p.stem.isdigit() and p.suffix in ('.dds', '.png')}
    result = []
    for filename in sorted(selected):
        source = root / 'shared/images' / filename
        if not source.exists():
            source = folder / filename
        shape, data = pixels(source)
        candidates = []
        for target, (other_shape, other) in existing.items():
            if shape != other_shape:
                continue
            pairs = Counter((a, b) for a, b in zip(data, other) if a != b)
            changes = {}
            if shape[2] == 'L':
                for owner in sorted({owner for owner, _ in refs[filename]}):
                    pal = palettes[owner]
                    rows = []
                    for row in range(8):
                        count = 0
                        for (a, b), amount in pairs.items():
                            ca, cb = pal[row * 256 + a], pal[row * 256 + b]
                            if ca[3] != cb[3] or ((ca[3] or cb[3]) and ca[:3] != cb[:3]):
                                count += amount
                        rows.append(count)
                    changes[owner] = rows
            candidates.append({'target': target.relative_to(root).as_posix(),
                               'different_indices': sum(pairs.values()),
                               'changed_visible_pixels': changes,
                               'equivalent_all_palettes': bool(changes) and all(not any(v) for v in changes.values())})
        candidates.sort(key=lambda c: c['different_indices'])
        result.append({'file': filename, 'dimensions': shape[:2], 'manifest_references': refs[filename],
                       'support_script_references': uses[filename], 'body_script_references': body_uses[filename],
                       'candidates': candidates})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--support', default='えこ')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.assets, args.support)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'images': len(report),
                      'referenced_by_support_scripts': sum(bool(r['support_script_references']) for r in report),
                      'referenced_by_body_scripts': sum(bool(r['body_script_references']) for r in report),
                      'same_dimensions': sum(bool(r['candidates']) for r in report),
                      'identical_indices': sum(any(c['different_indices'] == 0 for c in r['candidates']) for r in report),
                      'equivalent_all_palettes': sum(any(c['equivalent_all_palettes'] for c in r['candidates']) for r in report)}, indent=2))


if __name__ == '__main__':
    main()
