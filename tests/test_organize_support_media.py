import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/fm2k_convert"))
import organize_support_media as organize
from supports import SUPPORTS


def fixture(root):
    pool = root / "shared/sounds"
    pool.mkdir(parents=True)
    files = []
    for data in (b"exclusive", b"two supports", b"fighter also uses this"):
        path = pool / (hashlib.sha1(data).hexdigest() + ".wav")
        path.write_bytes(data)
        files.append(path)
    manifest = "".join('{ shared = "sounds/%s" },\n' % p.name for p in files)
    common = root / "supports/common"
    common.mkdir(parents=True)
    (common / "sounds.lton").write_text(manifest, encoding="utf-8")
    (common / "images.lton").write_text("nil^,\n", encoding="utf-8")
    for name in SUPPORTS:
        directory = root / "supports" / name
        directory.mkdir(parents=True)
        used = [0, 1, 2] if name == "えこ" else [1] if name == "シエラ" else []
        blocks = "".join('    { "S", %d },\n' % i for i in used)
        (directory / "script.lton").write_text('{ name = "test", level = 0, blocks = {\n' + blocks + '} },\n', encoding="utf-8")
    fighter = root / "characters/test"
    fighter.mkdir(parents=True)
    (fighter / "sounds.lton").write_text(manifest, encoding="utf-8")
    (fighter / "script.lton").write_text('{ name = "test", level = 0, blocks = {\n    { "S", 2 },\n} },\n', encoding="utf-8")
    return files, manifest


class OrganizeSupportMediaTest(unittest.TestCase):
    def test_exclusivity_all_references_and_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, manifest = fixture(root)
            moves, rewritten = organize.plan(root)
            target = root / "supports/えこ/sounds/0000.wav"
            self.assertEqual(moves, {files[0]: target})
            self.assertEqual(len(rewritten), 2)
            organize.apply(root, moves, rewritten)
            self.assertEqual(target.read_bytes(), b"exclusive")
            self.assertFalse(files[0].exists())
            self.assertTrue(all(p.exists() for p in files[1:]))
            self.assertEqual(organize.plan(root), ({}, {}))
            # A regenerated fighter may refer to a newly created pool copy.
            files[0].write_bytes(b"exclusive")
            (root / "characters/test/sounds.lton").write_text(manifest, encoding="utf-8")
            moves, rewritten = organize.plan(root)
            self.assertEqual(moves, {files[0]: target})
            organize.apply(root, moves, rewritten)
            self.assertEqual(organize.plan(root), ({}, {}))

    def test_conflicting_destination_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, manifest = fixture(root)
            target = root / "supports/えこ/sounds/0000.wav"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                organize.plan(root)
            self.assertTrue(files[0].exists())
            self.assertEqual((root / "supports/common/sounds.lton").read_text(encoding="utf-8"), manifest)


if __name__ == "__main__":
    unittest.main()
