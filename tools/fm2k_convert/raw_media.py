"""Media-only FM2K reader. Layout/RLE reference: xem85/fm2ndparser BaseParser.

See licenses/fm2ndparser.txt for attribution. Does not parse or emit skills.
"""
import hashlib
import struct
from PIL import Image
from convert import palette_rgba, dds_l8_header


def unpack_sprite(data, size):
    out = bytearray()
    at = 0
    while at < len(data) and len(out) < size:
        control = data[at]
        at += 1
        mode, count = control >> 6, control & 63
        if count == 0:
            count = data[at]
            at += 1
            if count:
                count += 63
            else:
                count = int.from_bytes(data[at:at + 3], 'little') + 319
                at += 3
        count = min(count, size - len(out))
        if mode == 0:
            out.extend(bytes(count))
        elif mode == 1:
            out.extend(data[at:at + count])
            at += count
        elif mode == 2:
            out.extend(bytes([data[at]]) * count)
            at += 1
        else:
            distance = data[at]
            at += 1
            if distance == 0:
                distance = (data[at] + 1) << 8
                at += 2
            if distance > len(out):
                raise ValueError('Invalid FM2K back-reference')
            pattern = out[-distance:]
            out.extend((pattern * ((count + distance - 1) // distance))[:count])
    if len(out) != size:
        raise ValueError('Truncated FM2K sprite')
    return bytes(out)


def image_key(mode, size, pixels):
    return hashlib.sha1(f'{size[0]}x{size[1]}:{mode}:'.encode() + pixels).hexdigest()


def media(path):
    data = path.read_bytes()
    if not data.startswith(b'2DKGT'):
        raise ValueError(f'Not an FM2K file: {path}')
    at = 272

    def take(size):
        nonlocal at
        if size < 0 or at + size > len(data):
            raise ValueError(f'Truncated FM2K file: {path} at {at}')
        result = data[at:at + size]
        at += size
        return result

    def uint():
        return struct.unpack('<I', take(4))[0]

    take(uint() * 39)
    take(uint() * 16)
    for i in range(uint()):
        _, w, h, palette, packed = struct.unpack('<5I', take(20))
        if not w or not h:
            take(packed)
            continue
        if palette not in (0, 1) or w * h > 64 * 1024 * 1024:
            raise ValueError(f'Unsupported image layout: {path} #{i}')
        size = w * h + (1024 if palette else 0)
        raw = unpack_sprite(take(packed), size) if packed else take(size)
        if palette:
            image = Image.frombytes('P', (w, h), raw[1024:])
            image.putpalette([c for color in palette_rgba(raw[:1024]) for c in color], rawmode='RGBA')
            image = image.convert('RGBA')
            yield image_key('RGBA', (w, h), image.tobytes()), image
        else:
            yield image_key('L', (w, h), raw), dds_l8_header(w, h) + raw
    palette_rows = [take(1056)[:1024] for _ in range(8)]
    pixels = bytes(c for row in palette_rows for color in palette_rgba(row) for c in color)
    yield image_key('RGBA', (256, 8), pixels), Image.frombytes('RGBA', (256, 8), pixels)
    for i in range(uint()):
        take(36)
        size = uint()
        take(2)
        raw = take(size)
        if raw:
            yield hashlib.sha1(raw).hexdigest(), raw
