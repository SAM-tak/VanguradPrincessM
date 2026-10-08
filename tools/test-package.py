"""Compare direct packaging with the old copied tree, then run it on the VM."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--love', type=Path, default=Path('C:/Users/Owner/source/repos/lhat-love'))
    args = parser.parse_args()
    compiler = args.love / 'build/love/Release/lovec.exe'
    vm = args.love / 'build-vmonly-shipping/love/Release/love.exe'
    package = Path(__file__).with_name('package-game.ps1')

    def run(*command, expected=0):
        result = subprocess.run(list(map(str, command)), capture_output=True,
                                encoding='utf-8', errors='replace', timeout=60)
        assert result.returncode == expected, (command, result.returncode, result.stdout, result.stderr)
        return result

    with tempfile.TemporaryDirectory(prefix='vp-package-') as directory:
        root = Path(directory)
        source = root / 'source with spaces'
        files = {
            'main.lh': '''module^packagetest
import^std.lton
import^love.filesystem
let^helper = require^"src/helper.lh"
public^let^run = p^{
    let^text = love.filesystem.read("assets/日本語 [asset].txt")
    if^text != "asset payload" { return^1 }
    let^data = std.lton.load("data/日本語/settings.lton")
    if^data fits^t^{ value : number^ } { return^data.value + helper.value() }
    return^2
}
'''.encode(),
            'conf.lton': b'window = false^, modules = { audio = false^, graphics = false^ }',
            'src/helper.lh': b'module^helper\npublic^let^value = f^ -> number^ { 7 }',
            'src/unreferenced.lh': b'module^unreferenced\npublic^let^value = 23',
            'data/日本語/settings.lton': b'value = 10',
            'data/other/settings.lton': b'value = 99',
            'assets/日本語 [asset].txt': b'asset payload',
            'assets/raw.bin': bytes(range(256)),
            'data/retained.txt': b'keep non-LTON data',
        }
        excluded = {
            'assets/nested/skills/invalid.lh', 'data/_conversion/invalid.lton',
            'data/nested/data.lton', 'assets/support-source.lton',
            'tools/private.txt', 'unselected.txt',
        }
        for name, content in files.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for name in excluded:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'deliberately invalid source')
        (source / 'assets/empty').mkdir()
        empty_dirs = {'assets/empty/', 'assets/nested/', 'data/nested/'}

        archive = root / 'game.love'
        work = root / 'work'
        def pack(workdir, expected=0, jobs=1):
            return run('pwsh', '-NoProfile', '-File', package, '-SourceRoot', source,
                       '-Lovec', compiler, '-WorkDirectory', workdir, '-Archive', archive,
                       '-Jobs', jobs, expected=expected)
        pack(work)
        units = {name for name in files if name.endswith(('.lh', '.lton'))}
        for folder in ('source', 'compiled'):
            assert {p.relative_to(work / folder).as_posix()
                    for p in (work / folder).rglob('*') if p.is_file()} == units

        baseline_source = root / 'old stage'
        for name, content in files.items():
            target = baseline_source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        baseline = root / 'old game'
        run(compiler, '--no-error-screen', '--compile-game', baseline, baseline_source)
        with zipfile.ZipFile(archive) as zipped:
            assert len(zipped.namelist()) == len(files) + len(empty_dirs)
            assert set(zipped.namelist()) == set(files) | empty_dirs
            for name in files:
                assert zipped.read(name) == (baseline / name).read_bytes(), name
                if name in units:
                    assert zipped.read(name) != files[name], name
        run(vm, '--no-error-screen', archive, expected=17)

        with zipfile.ZipFile(archive) as zipped:
            serial = {name: zipped.read(name) for name in zipped.namelist()}
        parallel_work = root / 'parallel work'
        result = pack(parallel_work, jobs=6)
        assert 'with 3 threads' in result.stdout, result.stdout
        with zipfile.ZipFile(archive) as zipped:
            assert {name: zipped.read(name) for name in zipped.namelist()} == serial
        assert {p.relative_to(parallel_work / 'compiled').as_posix()
                for p in (parallel_work / 'compiled').rglob('*') if p.is_file()} == units
        assert len(list((parallel_work / 'source').rglob('*.lton'))) == 3
        assert not (parallel_work / 'lton').exists()
        run(vm, '--no-error-screen', archive, expected=17)

        saved_archive = archive.read_bytes()
        result = pack(work, expected=1)
        assert 'already exists' in result.stderr
        (source / 'data/bad.lton').write_bytes(b'value =')
        result = pack(root / 'failed work', expected=1, jobs=6)
        assert 'bad.lton' in result.stderr, result.stderr
        assert archive.read_bytes() == saved_archive
        assert not list(root.glob('*.tmp'))
        for name, content in files.items():
            assert (source / name).read_bytes() == content
    print('PASS: serial/parallel binary equivalence, archive contents, exclusions, VM execution, worker failure preservation')


if __name__ == '__main__':
    main()
