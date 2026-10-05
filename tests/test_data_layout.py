import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
from convert import convert
from layout import metadata_path
import organize_support_media as organize
from test_organize_support_media import fixture


class DataLayoutTest(unittest.TestCase):
    def test_conversion_separates_definitions_and_legacy_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            source = project / 'example.json'
            source.write_text(json.dumps(dict(name='example', type=0, images=[],
                sounds=[], globalPalettes=[], skills=[dict(name='idle', type=0, blocks=[])])))
            convert(source, project / 'assets', 'character', media=False)
            media = project / 'assets/characters/example'
            definitions = project / 'data/characters/example'
            self.assertTrue((media / 'skills/0000.lton').exists())
            for filename in ('images.lton', 'sounds.lton', 'data.lton'):
                self.assertTrue((definitions / filename).exists())
                self.assertFalse((media / filename).exists())

    def test_support_media_moves_binaries_but_rewrites_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'
            files, _ = fixture(root)
            for path in list(root.rglob('*.lton')):
                destination = metadata_path(path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                path.rename(destination)
            moves, rewritten = organize.plan(root)
            self.assertEqual(moves, {files[0]: root / 'supports/えこ/sounds/0000.wav'})
            self.assertTrue(all((Path(tmp) / 'data') in p.parents for p in rewritten))
            organize.apply(root, moves, rewritten)
            self.assertEqual(organize.plan(root), ({}, {}))
            self.assertEqual(list(root.rglob('*.lton')), [])


if __name__ == '__main__':
    unittest.main()
