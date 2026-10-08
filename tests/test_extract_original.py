from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
import py7zr
from extract_original import SIGNATURE, archive_region, extract, validate_members


class ExtractOriginalTest(unittest.TestCase):
    def make_archive(self, root):
        source = root / 'plain.7z'
        with py7zr.SevenZipFile(source, 'w') as archive:
            archive.writestr(b'original player data', 'ゲーム/ゆい.player')
            archive.writestr(b'original game data', 'ゲーム/ゲーム.kgt')
            archive.writestr(b'not needed', 'ゲーム/ゲーム.exe')
        return source

    def test_plain_and_sfx_with_false_signature_and_trailer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plain = self.make_archive(root)
            stub = b'MZ' + SIGNATURE + bytes(50) + b'not an executable'
            sfx = root / 'original.exe'
            sfx.write_bytes(stub + plain.read_bytes() + b'trailer')
            self.assertEqual(archive_region(sfx), (len(stub), plain.stat().st_size))
            for i, source in enumerate((plain, sfx)):
                with redirect_stdout(io.StringIO()):
                    extract(source, root / f'out{i}')
                self.assertEqual((root / f'out{i}/ゲーム/ゆい.player').read_bytes(), b'original player data')
                self.assertFalse((root / f'out{i}/ゲーム/ゲーム.exe').exists())

    def test_list_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_archive(root)
            output = root / 'output'
            log = io.StringIO()
            with redirect_stdout(log):
                extract(source, output, list_only=True)
            self.assertIn('ゆい.player', log.getvalue())
            self.assertFalse(output.exists())
            output.mkdir()
            with self.assertRaises(FileExistsError):
                extract(source, output)

    def test_invalid_and_truncated_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            source = self.make_archive(Path(temp))
            raw = source.read_bytes()
            for damaged in (b'MZ', raw[:-1], raw[:8] + bytes(4) + raw[12:]):
                source.write_bytes(damaged)
                with self.assertRaises(ValueError):
                    archive_region(source)

    def test_paths_and_links(self):
        def member(name, symlink=False):
            return SimpleNamespace(filename=name, is_directory=False, is_file=not symlink, is_symlink=symlink)
        for name in ('../escape', '/absolute', 'C:/absolute', 'a\\..\\escape', 'a/../escape'):
            with self.assertRaises(ValueError):
                validate_members([member(name)])
        with self.assertRaises(ValueError):
            validate_members([member('link', True)])
        with self.assertRaises(ValueError):
            validate_members([member('same'), member('SAME')])


if __name__ == '__main__':
    unittest.main()
