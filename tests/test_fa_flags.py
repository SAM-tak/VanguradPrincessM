"""The parser's halfed bit must not be mistaken for projectile cancellation."""
import copy
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
from gen_script import block, restore_fa_flags


class RawFAFlags(unittest.TestCase):
    def test_unknown_db_is_restored_with_both_flags_and_branch(self):
        raw = bytearray(0x114 + 39 + 4 + 16)
        struct.pack_into('<I', raw, 0x110, 1)
        struct.pack_into('<I', raw, 0x114 + 39, 1)
        offset = 0x114 + 39 + 4
        struct.pack_into('<BBHB', raw, offset, 22, 3, 769, 17)
        raw[offset + 7] = 5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.player'
            path.write_bytes(raw)
            data = {'skills': [{'blocks': [{'type': 'Unknown'}]}]}
            restore_fa_flags(path, data)
            self.assertEqual(block(data['skills'][0]['blocks'][0]), ['DB', 5, 1, 1, 769, 17])

    def test_bit15_is_preserved_separately(self):
        for flags in (0, 4, 0x8000, 0x8004):
            raw = bytearray(0x114 + 39 + 4 + 32)
            struct.pack_into('<I', raw, 0x110, 1)
            struct.pack_into('<I', raw, 0x114 + 39, 2)
            struct.pack_into('<BhhhhBHB', raw, 0x114 + 39 + 4 + 16,
                             24, 1, -2, 3, 4, 0, flags, 5)
            fa = dict(type='FA', x=1, y=-2, width=3, height=4, number=0,
                      power=5, halfed=bool(flags & 4))
            data = {'skills': [{'blocks': [{'type': 'Settings'}, copy.copy(fa)]}]}
            with tempfile.NamedTemporaryFile(suffix='.player', delete=False) as f:
                f.write(raw)
                path = Path(f.name)
            try:
                restore_fa_flags(path, data)
                converted = block(data['skills'][0]['blocks'][1])[-1].split()
                self.assertEqual('projectileCancel' in converted, bool(flags & 0x8000))
                self.assertEqual('halfed' in converted, bool(flags & 4))
                data['skills'][0]['blocks'][1]['x'] = 99
                with self.assertRaises(ValueError):
                    restore_fa_flags(path, data)
            finally:
                path.unlink()


if __name__ == '__main__':
    unittest.main()
