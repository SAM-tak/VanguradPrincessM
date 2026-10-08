"""Extract original game data from 7z/SFX, omitting Windows executables and DLLs."""
import argparse
import mmap
from pathlib import Path, PurePosixPath
import struct
import tempfile
import zlib

import py7zr

SIGNATURE = bytes.fromhex('377abcaf271c')


def archive_region(source):
    """Locate and validate the start and next headers; never assume a stub size."""
    with source.open('rb') as file:
        if source.stat().st_size < 32:
            raise ValueError('No valid 7z archive header found')
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
            at = data.find(SIGNATURE)
            while at >= 0:
                if at + 32 <= len(data):
                    crc, offset, size, next_crc = struct.unpack_from('<IQQI', data, at + 8)
                    start = at + 32 + offset
                    end = start + size
                    if (zlib.crc32(data[at + 12:at + 32]) == crc
                            and end <= len(data) and size > 0
                            and zlib.crc32(data[start:end]) == next_crc):
                        return at, end - at
                at = data.find(SIGNATURE, at + 1)
    raise ValueError('No valid 7z archive header found (unsupported or damaged file)')


def validate_members(members):
    seen = set()
    for member in members:
        name = member.filename
        parts = name.split('/')
        if (not name or '\\' in name or ':' in name or PurePosixPath(name).is_absolute()
                or any(p in ('', '.', '..') for p in parts)):
            raise ValueError(f'Unsafe archive path: {name!r}')
        if member.is_symlink or not (member.is_directory or member.is_file):
            raise ValueError(f'Unsupported archive link or special file: {name!r}')
        key = name.casefold()
        if key in seen:
            raise ValueError(f'Duplicate archive path: {name!r}')
        seen.add(key)


def extract(source, destination, list_only=False):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if not list_only and (destination.exists() or destination.is_symlink()):
        raise FileExistsError(f'Output already exists; choose a new directory: {destination}')
    offset, length = archive_region(source)
    print(f'7z archive: offset={offset}, bytes={length}', flush=True)
    parent = destination.parent.resolve() if not list_only else Path(tempfile.gettempdir()).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vanpri-extract-', dir=parent) as temporary:
        staging = Path(temporary).resolve()
        assert staging.parent == parent
        archive = staging / 'payload.7z'
        with source.open('rb') as src, archive.open('wb') as dst:
            src.seek(offset)
            remaining = length
            while remaining:
                chunk = src.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError('Truncated input archive')
                dst.write(chunk)
                remaining -= len(chunk)
        # Passing a stream also keeps extraction sequential: a failed worker
        # must not outlive the archive and lock the staging file on Windows.
        with archive.open('rb') as stream, py7zr.SevenZipFile(stream, 'r') as seven:
            if seven.needs_password():
                raise ValueError('Password-protected archives are not supported')
            members = seven.list()
            validate_members(members)
            if list_only:
                for member in members:
                    print(member.filename)
                return
            # The original Windows game executable uses BCJ2 (unsupported by
            # py7zr), in a separate folder/stream. It is not a converter input.
            skipped = [m for m in members if PurePosixPath(m.filename).suffix.lower() in ('.exe', '.dll')]
            for member in skipped:
                print(f'Skipping Windows program (not needed for conversion): {member.filename}', flush=True)
            members = [m for m in members if m not in skipped]
            print(f'Extracting {len(members)} entries ({sum(m.uncompressed for m in members)} bytes)...', flush=True)
            output = staging / 'output'
            output.mkdir()
            seven.extract(path=output, targets=[m.filename for m in members])
        # Verify the actual extracted files before making the output visible.
        for member in members:
            path = output / member.filename
            if member.is_file:
                if not path.is_file() or path.stat().st_size != member.uncompressed:
                    raise ValueError(f'Incomplete extraction: {member.filename}')
                if member.crc32 is not None:
                    crc = 0
                    with path.open('rb') as file:
                        while chunk := file.read(1024 * 1024):
                            crc = zlib.crc32(chunk, crc)
                    if crc != member.crc32:
                        raise ValueError(f'CRC mismatch: {member.filename}')
        if destination.exists():
            raise FileExistsError(f'Output appeared during extraction: {destination}')
        output.rename(destination)
    print(f'Extracted to: {destination}', flush=True)
    for game in sorted(destination.rglob('*.kgt')):
        print(f'FM2K input: {game}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='vanpri108.exe or a plain .7z archive')
    parser.add_argument('destination', type=Path, nargs='?', help='New directory for original game files')
    parser.add_argument('--list', action='store_true', help='List contents without extracting')
    args = parser.parse_args()
    if args.destination is None and not args.list:
        parser.error('destination is required unless --list is used')
    try:
        extract(args.source, args.destination or Path('.'), args.list)
    except (OSError, ValueError, py7zr.exceptions.ArchiveError) as error:
        parser.exit(1, f'Extraction failed: {error}\n')


if __name__ == '__main__':
    main()
