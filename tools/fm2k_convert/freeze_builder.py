"""Build a native standalone asset builder using the current Python environment."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    source = Path(__file__).resolve().parent
    root = source.parent.parent
    work = root / 'build' / 'asset-builder-freeze'
    output = root / 'build' / 'asset-builder-native'
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--onefile', '--console', '--name', 'BuildAssets',
        '--distpath', str(output), '--workpath', str(work / 'work'),
        '--specpath', str(work),
        '--add-data', f'{source / "assets-recipe.json"}:.',
        str(source / 'build_assets.py'),
    ], check=True)
    # Ship dependency notices alongside the executable, including the interpreter.
    notices = output / 'asset-builder-licenses'
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / 'licenses' / 'fm2ndparser.txt', notices / 'fm2ndparser.txt')
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.exists():
        python_license = Path(sys.base_prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'LICENSE.txt'
    if not python_license.exists():
        raise FileNotFoundError('Python LICENSE.txt is required for distribution')
    shutil.copyfile(python_license, notices / 'Python.txt')
    for package in distributions():
        for entry in package.files or ():
            if not any(word in entry.name.lower() for word in ('license', 'copying', 'notice')):
                continue
            src = Path(package.locate_file(entry))
            if src.is_file():
                dest = notices / package.metadata['Name'] / str(entry).replace('/', '__').replace('\\', '__')
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
    print(f'Built standalone asset builder: {output}')


if __name__ == '__main__':
    main()
