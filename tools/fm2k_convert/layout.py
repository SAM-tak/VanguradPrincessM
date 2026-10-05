"""Physical layout: media in assets/, versioned definitions in data/."""
from pathlib import Path


def _replace_root(path, old, new):
    path = Path(path)
    for parent in (path, *path.parents):
        if parent.name == old:
            return parent.with_name(new) / path.relative_to(parent)
    return path


def metadata_path(path):
    return _replace_root(path, 'assets', 'data')


def media_path(path):
    return _replace_root(path, 'data', 'assets')


def conversion_path(path):
    path = Path(path)
    for parent in path.parents:
        if parent.name == 'data':
            return parent / '_conversion' / path.relative_to(parent)
    return path


def runtime_path(path):
    path = Path(path)
    for parent in path.parents:
        if parent.name == '_conversion':
            return parent.parent / path.relative_to(parent)
    return path
