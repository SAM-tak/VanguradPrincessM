"""Restore omitted EB operands from untouched extraction LTON, without renumbering.

Run from the project root: python tools/fm2k_convert/restore_shake.py [--apply]
Reads only the exact verbose format emitted by convert.py. Ambiguous skill names,
different EB sequences or missing source data fail before any file is written.
Both runtime definitions and support conversion inputs are updated, retaining
their media remaps, namespaces, patches, and canonical Yui support definitions.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from gen_script import block, lton_list

STRING = r'"(?:[^"\\]|\\.)*"'


def raw_skills(folder):
    result = defaultdict(list)
    for path in sorted(folder.glob('*.lton')):
        text = path.read_text(encoding='utf-8')
        heads = list(re.finditer(r'^    name = (' + STRING + r'),$', text, re.M))
        first = int(re.search(r'^first = (\d+),', text, re.M)[1])
        for i, head in enumerate(heads):
            name = json.loads(head[1])
            body = text[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
            effects = []
            for match in re.finditer(r'^            type = "EB",.*?^        },', body, re.M | re.S):
                raw = match[0]
                value = {'type': 'EB'}
                for key in ('fadingType', 'duration'):
                    value[key] = int(re.search(r'\b' + key + r' = (-?\d+)', raw)[1])
                for key in ('rgba', 'shakeBgX', 'shakeBgY'):
                    table = re.search(r'\b' + key + r' = \{([^}]+)\}', raw)[1]
                    value[key] = {k: int(v) for k, v in re.findall(r'(\w+) = (-?\d+)', table)}
                for key in ('player', 'enemy', 'bg', 'system'):
                    value[key] = re.search(r'\b' + key + r' = (true|false)\^', raw)[1] == 'true'
                effects.append(block(value))
            result[name].append(effects)
            result[f'#{first + i}'] = [effects]
    return result


def restore(text, sources, yui):
    heads = list(re.finditer(r'^\{ name = (' + STRING + r'),', text, re.M))
    replacements = []
    for i, head in enumerate(heads):
        name = json.loads(head[1])
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head.start():end]
        effects = list(re.finditer(r'^    \{ "EB",.*? \},$', body, re.M))
        if not effects:
            continue
        helper = re.match(r'共通サポート補助_(\d+)_', name)
        candidates = yui.get('#' + helper[1], []) if helper else sources.get(name, [])
        current = [json.loads('[' + e[0].strip()[1:-2] + ']') for e in effects]
        legacy = lambda b: b[:7] + [b[-1]]
        candidates = [c for c in candidates if list(map(legacy, c)) == list(map(legacy, current))]
        unique = {json.dumps(c, ensure_ascii=False) for c in candidates}
        if len(unique) != 1:
            raise ValueError(f'{name}: expected one matching original EB sequence, got {len(unique)}')
        original = json.loads(unique.pop())
        for match, old, new in zip(effects, current, original):
            if len(old) not in (8, 14) or (len(old) == 14 and old != new):
                raise ValueError(f'{name}: conflicting restored EB: {old}')
            if old != new:
                replacements.append((head.start() + match.start(), head.start() + match.end(),
                                     '    ' + lton_list(new) + ','))
    for start, end, value in reversed(replacements):
        text = text[:start] + value + text[end:]
    return text, len(replacements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    yui = raw_skills(Path('assets/characters/ゆい/skills'))
    cache, pending = {}, []
    files = sorted(Path('data').rglob('script.lton')) + sorted(Path('data/_conversion').rglob('support-source.lton'))
    for path in files:
        relative = path.relative_to('data')
        if relative.parts[0] == '_conversion':
            relative = Path(*relative.parts[1:])
        folder = Path('assets') / relative.parent / 'skills'
        if relative.parts[0] == 'supports':
            sources = yui
        else:
            if folder not in cache:
                cache[folder] = raw_skills(folder)
            sources = cache[folder]
        try:
            text, count = restore(path.read_text(encoding='utf-8'), sources, yui)
        except ValueError as error:
            raise ValueError(f'{path}: {error}') from error
        if count:
            pending.append((path, text, count))
    for path, text, count in pending:
        print(f'{path}: {count} EB blocks')
        if args.apply:
            path.write_text(text, encoding='utf-8', newline='\n')
    print(f'{sum(count for _, _, count in pending)} blocks in {len(pending)} files; apply={args.apply}')


if __name__ == '__main__':
    main()
