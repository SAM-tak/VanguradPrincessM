import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/fm2k_convert"))

spec = importlib.util.spec_from_file_location(
    "share_assets", Path(__file__).resolve().parents[1] / "tools/fm2k_convert/share_assets.py")
sharing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sharing)


class OwnershipRepair(unittest.TestCase):
    def test_explicit_alias_uses_canonical_pixels_and_is_repeatable(self):
        from PIL import Image
        for pooled in (False, True):
            with self.subTest(pooled=pooled), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                folder = root / "characters/example"
                (folder / "images").mkdir(parents=True)
                variant = folder / "images/0000.png"
                original = folder / "images/0001.png"
                Image.new("L", (3, 2), 119).save(variant)
                Image.new("L", (3, 2), 34).save(original)
                source, target = sharing.content_key(variant), sharing.content_key(original)
                listing = folder / "images.lton"
                listing.write_text('{ file = "images/0000.png", width = 3, height = 2 },\n')
                aliases = root / "aliases.txt"
                aliases.write_text(source + " " + target + "\n")
                canonical = root / "shared/images" / (target + ".png")
                if pooled:
                    canonical.parent.mkdir(parents=True)
                    original.rename(canonical)
                with patch.object(sharing, "ALIASES", aliases):
                    sharing.apply_image_aliases(root, sharing.scan(root))
                    self.assertFalse(variant.exists())
                    self.assertEqual(sharing.content_key(canonical), target)
                    self.assertIn('shared = "images/%s.png"' % target, listing.read_text())
                    self.assertIn('width = 3, height = 2', listing.read_text())
                    before = listing.read_bytes()
                    sharing.apply_image_aliases(root, sharing.scan(root))
                    self.assertEqual(listing.read_bytes(), before)

    def test_restore_preserves_slots_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "shared/images"
            pool.mkdir(parents=True)
            from PIL import Image
            image = pool / "source.png"
            Image.new("RGBA", (2, 3), (255, 100, 50, 255)).save(image)
            key = sharing.content_key(image)
            image = image.rename(pool / (key + ".png"))
            entry = '{ shared = "images/%s.png", width = 2, height = 3, format = "rgba" },\n' % key
            for name in ("owner", "other"):
                folder = root / "characters" / name
                folder.mkdir(parents=True)
                (folder / "images.lton").write_text("# Header\nnil^,\n" + entry, encoding="utf-8")
            with patch.object(sharing, "owners", return_value={key: "owner"}):
                sharing.restore_owned_images(root)
                restored = root / "characters/owner/images/0001.png"
                self.assertEqual(sharing.content_key(restored), key)
                self.assertIn('file = "images/0001.png"', (restored.parent.parent / "images.lton").read_text())
                self.assertEqual((root / "characters/other/images.lton").read_text(), "# Header\nnil^,\nnil^,\n")
                self.assertFalse(image.exists())
                sharing.restore_owned_images(root)
                self.assertEqual(sharing.content_key(restored), key)

    def test_keep_pool_file_referenced_by_non_character(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "shared/images/abc.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"preserved")
            entry = '{ shared = "images/abc.png" },\n'
            for folder in (root / "characters/other", root / "demos/example"):
                folder.mkdir(parents=True)
                (folder / "images.lton").write_text(entry)
            with patch.object(sharing, "owners", return_value={"abc": "owner"}):
                sharing.restore_owned_images(root)
            self.assertTrue(image.exists())


if __name__ == "__main__":
    unittest.main()
