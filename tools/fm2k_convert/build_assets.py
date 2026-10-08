"""Build release-compatible assets from the original SFX/7z or game directory.

Only media is generated. Shipped game definitions are never regenerated.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path, PurePosixPath
import tempfile
import py7zr
from PIL import Image

from extract_original import extract
from raw_media import media
from share_assets import content_key, dds_pixels

DEFAULT_RECIPE = Path(__file__).with_name('assets-recipe.json')


def write_recipe(assets, destination):
    """Developer operation: capture the current organized media layout."""
    groups = defaultdict(list)
    for path in sorted(assets.rglob('*')):
        if not path.is_file():
            continue
        if path.name == 'palettes.png' or (path.parent.name in ('images', 'sounds') and path.suffix in ('.png', '.dds', '.wav')):
            groups[content_key(path)].append(path.relative_to(assets).as_posix())
    destination.write_text(json.dumps({'version': 1, 'media': dict(sorted(groups.items()))}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'Recipe: {sum(map(len, groups.values()))} files, {len(groups)} unique contents')


def load_recipe(path):
    recipe = json.loads(path.read_text(encoding='utf-8'))
    if recipe.get('version') != 1 or not recipe.get('media'):
        raise ValueError('Unsupported or empty assets recipe')
    seen = set()
    for key, paths in recipe['media'].items():
        if len(key) != 40 or any(c not in '0123456789abcdef' for c in key) or not paths:
            raise ValueError('Invalid recipe content key')
        for value in paths:
            p = PurePosixPath(value)
            if p.is_absolute() or '\\' in value or ':' in value or any(part in ('', '.', '..') for part in value.split('/')):
                raise ValueError(f'Invalid output path: {value}')
            if value.casefold() in seen:
                raise ValueError(f'Duplicate output path: {value}')
            seen.add(value.casefold())
    return recipe['media']


def game_directory(source):
    games = sorted(source.rglob('*.kgt'))
    if len(games) != 1:
        raise ValueError(f'Expected one .kgt file, found {len(games)} in {source}')
    return games[0].parent


def build(source, destination, recipe_path=DEFAULT_RECIPE):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Output exists; choose a new assets directory: {destination}')
    required = load_recipe(recipe_path)
    remaining = dict(required)
    parent = destination.parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vanpri-assets-', dir=parent) as temporary:
        staging = Path(temporary).resolve()
        assert staging.parent == parent
        original = source
        if source.is_file():
            original = staging / 'original'
            extract(source, original)
        game = game_directory(original)
        output = staging / 'assets'
        output.mkdir()
        files = sorted(p for p in game.iterdir() if p.suffix.lower() in ('.kgt', '.player', '.stage', '.demo'))
        for i, path in enumerate(files):
            print(f'[{i + 1}/{len(files)}] {path.name}', flush=True)
            for key, payload in media(path):
                targets = remaining.pop(key, [])
                for relative in targets:
                    target = output / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if isinstance(payload, bytes) and payload.startswith(b'DDS ') and target.suffix == '.png':
                        w, h, pixels = dds_pixels(payload)
                        Image.frombytes('L', (w, h), pixels).save(target, optimize=True)
                    elif isinstance(payload, bytes):
                        target.write_bytes(payload)
                    else:
                        payload.save(target, optimize=True)
                    if content_key(target) != key:
                        raise ValueError(f'Generated content mismatch: {relative}')
        if remaining:
            missing = [p for paths in remaining.values() for p in paths]
            raise ValueError(f'{len(missing)} assets could not be reconstructed; source/version mismatch. Examples: {missing[:10]}')
        if destination.exists():
            raise FileExistsError(f'Output appeared during build: {destination}')
        output.rename(destination)
    print(f'Built {sum(map(len, required.values()))} verified files: {destination}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='vanpri108.exe, .7z, or extracted original directory')
    parser.add_argument('destination', type=Path, help='New assets directory (or recipe JSON with --write-recipe)')
    parser.add_argument('--recipe', type=Path, default=DEFAULT_RECIPE)
    parser.add_argument('--write-recipe', action='store_true', help='Developer only: source is an organized assets directory')
    args = parser.parse_args()
    try:
        if args.write_recipe:
            write_recipe(args.source, args.destination)
        else:
            build(args.source, args.destination, args.recipe)
    except (OSError, ValueError, py7zr.exceptions.ArchiveError) as error:
        parser.exit(1, f'Asset build failed: {error}\n')


if __name__ == '__main__':
    main()
