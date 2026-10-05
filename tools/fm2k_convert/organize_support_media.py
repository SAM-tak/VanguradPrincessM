"""Move provably exclusive support media out of shared, rewriting all manifests.

Run after share_assets.py and share_supports.py. Without --apply, report only.
Ambiguous media (multiple supports or non-support skill users) stays shared.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from layout import metadata_path, media_path
import re
import shutil

from share_assets import content_key
from supports import SUPPORTS, read_skills, source_script

REF = re.compile(r'\b(shared|file|asset) = "([^"]+)"')


def entries(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith(("{", "nil^"))]


def resolve(root, listing, line):
    match = REF.search(line)
    if not match:
        return None
    kind, value = match.groups()
    if kind == "shared":
        return (root / "shared" / value).resolve()
    if kind == "asset":
        # Virtual LOVE paths are rooted at assets, including in test fixtures.
        if not value.startswith("assets/"):
            raise ValueError(f"Unsupported asset path: {value}")
        return (root / value.removeprefix("assets/")).resolve()
    return (media_path(listing.parent) / value).resolve()


def plan(root):
    root = root.resolve()
    libraries = {}
    moves = {}
    for kind, op in (("images", "I"), ("sounds", "S")):
        listing = metadata_path(root) / "supports/common" / f"{kind}.lton"
        media = [resolve(root, listing, line) for line in entries(listing)]
        owners, numbers = defaultdict(set), defaultdict(set)
        # Already-moved assets still identify their shared hash on regeneration.
        pool_sources = {}
        for name in SUPPORTS:
            skills = read_skills(metadata_path(root) / "supports" / name / "script.lton", libraries)
            for skill in skills:
                for block in skill["blocks"]:
                    if block[0] != op or not 0 <= block[1] < len(media):
                        continue
                    path = media[block[1]]
                    if path is None:
                        continue
                    owners[path].add(name)
                    numbers[path].add(block[1])
        for path in owners:
            if not path.is_file():
                raise FileNotFoundError(path)
            if path.parent == root / "shared" / kind:
                pool_sources[path] = path
            elif (root / "supports") in path.parents:
                pool = root / "shared" / kind / (content_key(path) + path.suffix)
                if pool.exists():
                    pool_sources[path] = pool
        # Mere presence in each fighter's manifest does not imply ownership.
        # Inspect the actual non-bound skills, including demos and stages.
        other_users = set()
        for script in sorted(metadata_path(root).rglob("script.lton")):
            if (metadata_path(root) / "supports") in script.parents or "_conversion" in script.parts:
                continue
            local_listing = script.parent / f"{kind}.lton"
            if not local_listing.exists():
                continue
            local_media = [resolve(root, local_listing, line) for line in entries(local_listing)]
            skills = read_skills(script, libraries)
            parts = re.split(r'(?m)^\{ name = ', source_script(script).read_text(encoding="utf-8"))[1:]
            for skill, part in zip(skills, parts):
                if "support = " in part:
                    continue
                for block in skill["blocks"]:
                    if block[0] == op and 0 <= block[1] < len(local_media):
                        other_users.add(local_media[block[1]])
        for path, names in owners.items():
            source = pool_sources.get(path)
            if len(names) != 1 or source is None or path in other_users or source in other_users:
                continue
            name = next(iter(names))
            target = root / "supports" / name / kind / (f"{min(numbers[path]):04d}" + source.suffix)
            if source in moves and moves[source] != target:
                raise ValueError(f"Conflicting support ownership: {source}")
            if target.exists() and target.read_bytes() != source.read_bytes():
                raise ValueError(f"Refusing to overwrite different media: {target}")
            if target in moves.values() and moves.get(source) != target:
                raise ValueError(f"Conflicting destination: {target}")
            moves[source] = target
    rewritten = {}
    for kind in ("images", "sounds"):
        for listing in sorted(metadata_path(root).rglob(f"{kind}.lton")):
            lines = listing.read_text(encoding="utf-8").splitlines()
            changed = False
            for i, line in enumerate(lines):
                source = resolve(root, listing, line)
                if source not in moves:
                    continue
                target = moves[source]
                replacement = 'asset = "assets/%s"' % target.relative_to(root).as_posix()
                lines[i] = REF.sub(lambda _: replacement, line, count=1)
                changed = True
            if changed:
                rewritten[listing] = "\n".join(lines) + "\n"
    return moves, rewritten


def apply(root, moves, rewritten):
    root = root.resolve()
    # Copy and verify before changing references; delete only unreferenced pool files.
    for source, target in moves.items():
        if source.parent not in (root / "shared/images", root / "shared/sounds"):
            raise ValueError(f"Not a shared-pool source: {source}")
        if (root / "supports") not in target.resolve().parents:
            raise ValueError(f"Not a support destination: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError(f"Destination changed: {target}")
        shutil.copyfile(source, target)
        if source.read_bytes() != target.read_bytes():
            raise ValueError(f"Copy mismatch: {target}")
    for listing, text in rewritten.items():
        listing.write_text(text, encoding="utf-8", newline="\n")
    remaining = set()
    for kind in ("images", "sounds"):
        for listing in metadata_path(root).rglob(f"{kind}.lton"):
            remaining.update(resolve(root, listing, line) for line in entries(listing))
    for source in moves:
        if source in remaining:
            raise ValueError(f"Shared media still referenced: {source}")
    for source in moves:
        source.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    moves, rewritten = plan(args.assets)
    counts = Counter(f"{p.parent.parent.name}/{p.parent.name}" for p in moves.values())
    print(json.dumps({"files": len(moves), "manifests": len(rewritten), "counts": dict(sorted(counts.items()))}, ensure_ascii=False, indent=2))
    if args.apply:
        apply(args.assets, moves, rewritten)


if __name__ == "__main__":
    main()
