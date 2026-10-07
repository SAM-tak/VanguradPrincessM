"""Extract complete owner-specific supports. No Yui normalization or recipes.

Run gen_script.py on each original player first, then this tool. Original
numbered inputs remain in data/_conversion for reproducible extraction.
Media stays in the owner's existing manifests, which already share files.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from gen_script import lton_str
from layout import metadata_path, conversion_path
from share_supports import STARTS, skill_text
from support_namespaces import BANKS, ref_positions, emit
from supports import SUPPORTS, read_skills, source_script, named


def owner_hook(b):
    return b[0] == 'V' and b[1] == 76 and b[5:7] == [1, 93]


def groups_for(skills):
    starts = [named(skills, n) for n in STARTS.values()] + [named(skills, 'kage2  ')]
    assert starts == sorted(set(starts))
    return {name: list(range(starts[i], starts[i+1])) + [named(skills, SUPPORTS[name][2])]
            for i, name in enumerate(SUPPORTS)}


def helper_blocks(skills, core, entries):
    """Preserve helper entry offsets; never expose unrelated preceding code.

    A support entering E at owner voice block 3 must not execute the voice at
    block 1. Only reachable instructions are cloned; holes remain Nop so every
    original branch offset is exact. Full support bodies are kept verbatim.
    """
    wanted, todo = set(), list(entries)
    while todo:
        n, at = todo.pop()
        if n <= 0 or n in core:
            continue
        if not 0 <= n < len(skills):
            raise ValueError(f'Invalid helper {n}:{at}')
        bs = skills[n]['blocks']
        if at < 0 or at > len(bs):
            raise ValueError(f'Invalid helper entry {n}:{at}/{len(bs)}')
        while at < len(bs) and (n, at) not in wanted:
            wanted.add((n, at))
            b = bs[at]
            if not owner_hook(b):
                for k in ref_positions(b):
                    if b[k] > 0:
                        todo.append((b[k], b[k+1] if b[0] != 'C' else 0))
            if b[0] in ('E', 'SG'):
                break
            at += 1
    return wanted


def split(skills, owner):
    groups = groups_for(skills)
    mapping = {n: BANKS[name]+n for name, ns in groups.items() for n in ns}
    core = set(mapping)
    packages = {}
    package_maps = {}
    for name, ns in groups.items():
        entries = []
        for n in ns:
            for b in skills[n]['blocks']:
                if not owner_hook(b):
                    entries += [(b[k], b[k+1] if b[0] != 'C' else 0)
                                for k in ref_positions(b) if b[k] > 0]
        # Some effects live inside another support's original range. Clone the
        # referenced entry as a helper too: a selected package must be complete
        # without loading all of the other supports just to resolve that call.
        reachable = helper_blocks(skills, set(ns), entries)
        helpers = {n for n, _ in reachable}
        local = {**mapping, **{n: BANKS[name]+n for n in helpers}}
        package_maps[name] = {n: local[n] for n in set(ns) | helpers}
        result = []
        for n in sorted(set(ns) | helpers):
            sk = deepcopy(skills[n])
            if n in helpers:
                sk['name'] = f'helper:{n}:{sk["name"]}'
                sk['blocks'] = [b if (n, i) in reachable else ['Nop'] for i, b in enumerate(sk['blocks'])]
            for b in sk['blocks']:
                if owner == 'くるみ' and owner_hook(b) and b[7] not in core:
                    continue
                for k in ref_positions(b):
                    if b[k] > 0:
                        b[k] = local.get(b[k], b[k])
            result.append((BANKS[name]+n, sk))
        packages[name] = result
    body = []
    for n, source in enumerate(skills):
        if n in core:
            continue
        sk = deepcopy(source)
        for b in sk['blocks']:
            # A support-selection branch can enter a shared owner's helper,
            # not only a support's primary range (Yui's Sierra HUD is #403:10).
            # Enter its package copy so subsequent helper calls stay local.
            selected = next((name for name, spec in SUPPORTS.items()
                             if b[0] == 'V' and b[1] == 73 and b[5:7] == [1, spec[0]]), None)
            links = package_maps[selected] if selected else mapping
            for k in ref_positions(b):
                if b[k] > 0:
                    b[k] = links.get(b[k], mapping.get(b[k], b[k]))
        body.append((n, sk))
    return body, packages


def plan(root):
    root = metadata_path(root)
    outputs, report = {}, {}
    for path in sorted((root/'characters').glob('*/script.lton')):
        owner = path.parent.name
        if owner in ('だみー', 'ヒルダ'):
            continue
        source = source_script(path)
        text = source.read_text(encoding='utf-8')
        if 'support = ' in text:
            raise ValueError(f'{owner}: normalized input loses original differences; regenerate from player JSON first')
        skills = read_skills(source)
        body, packages = split(skills, owner)
        header = re.split(r'(?m)^\{ name = ', text, maxsplit=1)[0]
        # Persist the original conversion, not the split/relinked output.
        outputs[conversion_path(path.with_name('support-source.lton'))] = text
        outputs[path] = header + f'supportNamespaces = true^,\nsupportOwner = {lton_str(owner)},\n' + ''.join(emit(sk, n) for n, sk in body)
        for name, entries in packages.items():
            outputs[root/'supports'/name/f'{owner}.lton'] = (
                '# Complete original support definition for this owner; generated by owner_supports.py.\n'
                + ''.join(emit(sk, n, name, f'assets/characters/{owner}') for n, sk in entries))
        report[owner] = {'body': len(body), 'supports': {s: len(v) for s, v in packages.items()}}
    return outputs, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('data', type=Path)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    outputs, report = plan(args.data)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.apply:
        for path, text in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
