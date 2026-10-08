import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
from PIL import Image
from convert import write_dds_r8
from support_palettes import compatible, pattern, requirements, run


class SupportPalettesTest(unittest.TestCase):
    def test_shape_and_bijection(self):
        self.assertEqual(pattern(bytes([0, 2, 2, 4])), pattern(bytes([7, 9, 9, 3])))
        self.assertNotEqual(pattern(bytes([0, 2, 2, 4])), pattern(bytes([7, 9, 3, 3])))
        with self.assertRaises(ValueError):
            requirements(bytes([1, 1]), bytes([2, 3]), [(0, 0, 0, 0)] * 2048)

    def test_conflicting_palette_needs_another_bank(self):
        self.assertFalse(compatible({1: ('red',)}, {1: ('blue',)}))
        self.assertTrue(compatible({1: ('red',)}, {2: ('blue',)}))

    def test_apply_preserves_colors_and_is_repeatable(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / 'assets'
            images = root / 'supports/えこ/images'
            images.mkdir(parents=True)
            write_dds_r8(images / '0001.dds', 2, 2, bytes([0, 2, 2, 3]))
            write_dds_r8(images / 'variant.dds', 2, 2, bytes([0, 7, 7, 8]))
            owner = root / 'characters/ゆい'
            owner.mkdir(parents=True)
            raw = bytes(c for row in range(8) for i in range(256) for c in (i, row, 10, 255 if i else 0))
            Image.frombytes('RGBA', (256, 8), raw).save(owner / 'palettes.png')
            listing = Path(temp) / 'data/characters/ゆい/images.lton'
            listing.parent.mkdir(parents=True)
            listing.write_text('{ asset = "assets/supports/えこ/images/variant.dds", format = "indexed" },\n', encoding='utf-8')
            audit = run(root, 'えこ')
            self.assertEqual(audit['removable_images'], 1)
            self.assertTrue((images / 'variant.dds').exists())
            run(root, 'えこ', True)
            before = listing.read_bytes()
            self.assertFalse((images / 'variant.dds').exists())
            self.assertIn(b'palette = ', before)
            palette = next((Path(temp) / 'data/supports/えこ/palettes').glob('*.png'))
            with Image.open(palette) as image:
                for row in range(8):
                    self.assertEqual(image.getpixel((2, row)), (7, row, 10, 255))
                    self.assertEqual(image.getpixel((3, row)), (8, row, 10, 255))
            run(root, 'えこ', True)
            self.assertEqual(before, listing.read_bytes())


if __name__ == '__main__':
    unittest.main()
