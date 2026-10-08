"""Export explicit story routes and CPU patterns; no dummy fight at runtime.

The original parser discards the seven opponent records after reading them.
Recover those from the fixed 100 * 206 byte story table before the 4524 byte
tail. Layout reference: fm2ndparser PlayerParser.parseStoryEntryFightCpu.
Run from the game root: python tools/fm2k_convert/story.py
"""
from pathlib import Path
import re
import struct
from names import official

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT / 'vanpri108/ヴァンガードプリンセス'
CHARACTERS = ['ゆい', 'はるか', 'リリス', 'ルナ', 'くるみ', 'サキ', 'かえで', 'ナタリア', 'えり', 'あやね', 'ヒルダ', 'new1', '新2', 'だみー']
STAGES = ['スクール', 'プール', '神社', '瓦礫', '夜', '丘', 'ラスト']
DEMOS = ['モードセレクト', 'タイトル', 'キャラセレ', 'イージー', 'ノーマル', 'サバイバル', 'コンテニュー', 'ランダムみさき', 'ランダムかえで', 'ゆい勝ち', '丘イベント', 'イベントラスト', 'エンディング0', 'エンディング１', 'エンディング２', 'デモ 7']


def table_field(text, name):
    start = text.index(name + ' = {') + len(name) + 3
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == '{': depth += 1
        if text[pos] == '}':
            depth -= 1
            if depth == 0: return text[start:pos + 1]
    raise ValueError(name)


def export():
    for source in DONOR.glob('*.player'):
        name = official(source.stem)
        if name not in CHARACTERS[:11]: continue
        folder = ROOT / 'data/characters' / name
        data = folder.joinpath('data.lton').read_text(encoding='utf-8')
        from cpu_data import export_cpu
        export_cpu(source, table_field(data, 'commands'), table_field(data, 'cpu'), folder / 'cpu.lton')
        if name == 'ヒルダ': continue
        raw = source.read_bytes()
        start = len(raw) - 4524 - 20600
        assert raw[start:start + 3] == b'\x01\x01\x01', source
        assert raw[start + 28] == 14, 'preparation opponent must be dummy'
        scripts = re.split(r'(?m)^\{ name = ', folder.joinpath('script.lton').read_text(encoding='utf-8'))[1:]
        intro = int(re.findall(r'\{ "I", (\d+),', scripts[21])[-1])
        manifest = folder.joinpath('images.lton').read_text(encoding='utf-8').splitlines()[2:]
        entry = manifest[intro]
        assert 'width = 640, height = 480' in entry, (name, entry)
        ref = re.search(r'(file|shared) = "([^"]+)"', entry)
        path = f'assets/shared/{ref[2]}' if ref[1] == 'shared' else f'assets/characters/{name}/{ref[2]}'
        routes = [[], [], []]
        route = None
        for i in range(1, 100):
            e = raw[start + 206 * i:start + 206 * (i + 1)]
            if e[0] == 2:
                demo = struct.unpack_from('<H', e, 1)[0]
                if demo in (4, 5, 6): route = routes[demo - 4]
                elif route is not None and demo:
                    route.append(f'{{ kind = "demo", name = "{DEMOS[demo - 1]}", stage = "", level = 0, rounds = 0, seconds = 0 }}')
            elif e[0] == 1 and route is not None:
                cpus = [e[24 + 26 * k:50 + 26 * k] for k in range(7)]
                present = [c for c in cpus if c[4]]
                assert len(present) == 1, (name, i, 'multiple opponents')
                c = present[0]
                route.append(f'{{ kind = "fight", name = "{CHARACTERS[c[4] - 1]}", stage = "{STAGES[e[1] - 1]}", level = {c[5]}, rounds = {e[2]}, seconds = {struct.unpack_from("<H", e, 6)[0]} }}')
            elif e[0] == 4: route = None
        assert [sum('"fight"' in e for e in r) for r in routes] == [7, 7, 11], name
        text = f'# Original opponents and presentation assets, exported by story.py.\nintro = "{path}",\nroutes = {{\n'
        text += ''.join('    {\n' + ''.join('        ' + e + ',\n' for e in r) + '    },\n' for r in routes)
        folder.joinpath('story.lton').write_text(text + '},\n', encoding='utf-8', newline='\n')
        print(name, 'routes: 7 / 7 / 11')


if __name__ == '__main__': export()
