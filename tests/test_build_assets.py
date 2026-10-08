from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
from build_assets import build, load_recipe, game_directory
from raw_media import unpack_sprite, image_key


class BuildAssetsTest(unittest.TestCase):
    def test_sprite_modes(self):
        self.assertEqual(unpack_sprite(bytes([3, 0x42, 4, 5, 0x83, 7, 0xc4, 2]), 12), bytes([0, 0, 0, 4, 5, 7, 7, 7, 7, 7, 7, 7]))
        with self.assertRaises(ValueError):
            unpack_sprite(bytes([0xc1, 2]), 1)
        with self.assertRaises(ValueError):
            unpack_sprite(bytes([1]), 2)

    def test_full_build_from_synthetic_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / 'original'
            game.mkdir()
            data = b'2DKGT2G' + bytes(272 - 7)
            data += struct.pack('<III', 0, 0, 1)  # skills, blocks, images
            data += struct.pack('<5I', 0, 2, 1, 0, 0) + b'\x01\x02'
            data += bytes(1056 * 8) + struct.pack('<I', 0)
            (game / 'game.kgt').write_bytes(data)
            recipe = root / 'recipe.json'
            key = image_key('L', (2, 1), b'\x01\x02')
            recipe.write_text(json.dumps({'version': 1, 'media': {key: ['supports/えこ/images/test.dds', 'supports/えこ/images/test.png']}}))
            with redirect_stdout(io.StringIO()):
                build(game, root / 'assets', recipe)
            self.assertEqual((root / 'assets/supports/えこ/images/test.dds').read_bytes()[-2:], b'\x01\x02')
            self.assertTrue((root / 'assets/supports/えこ/images/test.png').read_bytes().startswith(b'\x89PNG'))
            with self.assertRaises(FileExistsError):
                build(game, root / 'assets', recipe)
            recipe.write_text(json.dumps({'version': 1, 'media': {'a' * 40: ['missing.dds']}}))
            with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                build(game, root / 'failed', recipe)
            self.assertFalse((root / 'failed').exists())

    def test_recipe_paths_and_ambiguous_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recipe = root / 'recipe.json'
            recipe.write_text(json.dumps({'version': 1, 'media': {'a' * 40: ['../bad']}}))
            with self.assertRaises(ValueError):
                load_recipe(recipe)
            for name in ('a.kgt', 'b.kgt'):
                (root / name).touch()
            with self.assertRaises(ValueError):
                game_directory(root)


if __name__ == '__main__':
    unittest.main()
