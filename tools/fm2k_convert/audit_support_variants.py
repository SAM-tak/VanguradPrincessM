"""Compare original support definitions with Yui, without changing runtime data.

Input is untouched fm2ndparser JSON, NOT the previously unified LTON. Ignore
inactive V operands, resolve asset contents, match skill references by identity,
and align branch destinations before reporting differences. Keep uncertain
matches visible; never infer that a behavior difference is a copying mistake.
"""
import argparse
import base64
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path

from gen_script import block
from names import official
from share_supports import ALIASES, STARTS, signature
from support_namespaces import ref_positions
from supports import SUPPORTS, identify


def clean(b):
    b = b[:]
    if b[0] == 'V':
        if b[2] == 0 and b[5] == 0:
            return ['Nop']
        if b[2] == 0:
            b[3:5] = [0, 0]
        if b[5] == 0:
            b[6:9] = [0, -1, 0]
    return b


def alignment(a, b):
    """Local block -> reference block, only for matched or paired instructions.

    Unlike block_map used when rewriting code, deletion does not silently map
    to the next instruction. An unmatched destination stays explicitly local.
    """
    result = {len(b): len(a)}
    sa, sb = [signature(x) for x in a], [signature(x) for x in b]
    for op, i, j, k, l in SequenceMatcher(None, sa, sb, autojunk=False).get_opcodes():
        if op == 'equal' or (op == 'replace' and j - i == l - k):
            for x, y in zip(range(i, j), range(k, l)):
                if a[x][0] == b[y][0]:
                    result[y] = x
    return result


class Source:
    def __init__(self, path):
        self.name = official(path.stem)
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        self.data = json.loads(path.read_text(encoding='utf-8-sig'))
        self.skills = self.data['skills']
        self.blocks = [[clean(block(b)) for b in s['blocks']] for s in self.skills]
        self.names = defaultdict(list)
        for i, s in enumerate(self.skills):
            self.names[s['name']].append(i)
        self.media_cache = {}

    def media(self, op, n):
        if (op, n) in self.media_cache:
            return self.media_cache[op, n]
        kind = 'images' if op == 'I' else 'sounds'
        entries = self.data[kind]
        if not 0 <= n < len(entries) or not entries[n].get('data'):
            key = 'empty'
        else:
            e = entries[n]
            raw = base64.b64decode(e['data'])
            if op == 'I':
                w, h = e['width'], e['height']
                if e['paletteType'] == 1:
                    # Compare visible RGBA, not unused private palette entries.
                    from convert import palette_rgba
                    palette = palette_rgba(raw[:1024])
                    pixels = bytes(c for p in raw[1024:1024+w*h] for c in palette[p])
                    head = f'{w}x{h}:rgba:'
                else:
                    # Global palette differences are reported separately. A
                    # support's already-approved shared palette stays separate
                    # from the action/geometry audit.
                    pixels = raw[:w*h]
                    head = f'{w}x{h}:indexed:'
                    used = set(pixels)
                    palettes = [base64.b64decode(p['data']) for p in self.data.get('globalPalettes', [])]
                    if palettes and all(not any(p[4*i:4*i+3]) for p in palettes for i in used):
                        pixels, head = b'', 'transparent:'
                raw = head.encode() + pixels
            else:
                raw += json.dumps([e.get('endlessLoop'), e.get('cddaTrack'), e.get('type')]).encode()
            key = hashlib.sha256(raw).hexdigest()
        self.media_cache[op, n] = key
        return key


def pair_skills(base, owner):
    pairs = {}
    for i, s in enumerate(base.skills):
        name = ALIASES.get((owner.name, s['name']), s['name'])
        # Auto-generated names are not identities across characters.
        if name.startswith('技名') or len(base.names[s['name']]) != 1:
            continue
        matches = owner.names.get(name, [])
        if len(matches) == 1:
            pairs[i] = matches[0]
    # Infer auto-numbered helpers from corresponding active call sites. Require
    # a unique, uncontested correspondence; record all other calls as different.
    while True:
        votes = defaultdict(Counter)
        for a, b in pairs.items():
            for y, x in alignment(base.blocks[a], owner.blocks[b]).items():
                if x == len(base.blocks[a]) or y == len(owner.blocks[b]):
                    continue
                aa, bb = base.blocks[a][x], owner.blocks[b][y]
                for k in set(ref_positions(aa)) & set(ref_positions(bb)):
                    u, v = aa[k], bb[k]
                    if 0 < u < len(base.skills) and 0 < v < len(owner.skills):
                        if base.skills[u]['name'].startswith('技名') or owner.skills[v]['name'].startswith('技名'):
                            votes[u][v] += 1
        additions = {u: next(iter(v)) for u, v in votes.items()
                     if u not in pairs and len(v) == 1 and next(iter(v)) not in pairs.values()}
        counts = Counter(additions.values())
        additions = {u: v for u, v in additions.items() if counts[v] == 1}
        if not additions:
            return pairs
        pairs.update(additions)


def canonical_blocks(source, index, reverse, positions, base=False):
    out = []
    for raw in source.blocks[index]:
        b = raw[:]
        if b[0] in ('I', 'S'):
            b[1] = source.media(b[0], b[1])
        for k in ref_positions(b):
            n = b[k]
            if n <= 0:
                continue
            if n in reverse:
                b[k] = f'skill:{reverse[n]}'
                if b[0] != 'C':
                    at = b[k+1]
                    b[k+1] = at if base else positions[n].get(at, f'local:{at}')
            else:
                b[k] = f'unmatched:{source.name}:{n}'
        out.append(b)
    return out


CATEGORIES = {'FA': 'attack', 'FD': 'hurtbox/pushbox', 'M': 'movement',
              'V': 'state/gauge/condition', 'I': 'image/timing/position',
              'S': 'sound', 'R': 'hit-reaction', 'O': 'spawn',
              'COM': 'input', 'SG': 'flow', 'DS': 'event', 'GP': 'life/special'}


def compare(base, owner, ids):
    pairs = pair_skills(base, owner)
    reverse = {v: k for k, v in pairs.items()}
    positions = {v: alignment(base.blocks[k], owner.blocks[v]) for k, v in pairs.items()}
    rows = []
    for n in ids:
        if n not in pairs:
            rows.append({'id': n, 'name': base.skills[n]['name'], 'unmatched': True})
            continue
        local = pairs[n]
        a = canonical_blocks(base, n, {i: i for i in range(len(base.skills))}, {}, True)
        b = canonical_blocks(owner, local, reverse, positions)
        changes = []
        for op, i, j, k, l in SequenceMatcher(None, list(map(tuple, a)), list(map(tuple, b)), autojunk=False).get_opcodes():
            if op == 'equal':
                continue
            changes.append({'operation': op, 'base_range': [i, j], 'owner_range': [k, l],
                            'base': base.blocks[n][i:j], 'owner': owner.blocks[local][k:l],
                            'semantic_base': a[i:j], 'semantic_owner': b[k:l],
                            'categories': sorted({CATEGORIES.get(x[0], x[0]) for x in a[i:j]+b[k:l]})})
        if changes:
            rows.append({'id': n, 'owner_id': local, 'name': base.skills[n]['name'], 'changes': changes})
    return rows


def action_costs(source):
    """Raw V71 deductions along the accepted HUD command's fallthrough.

    These are script units, not a claim about total consumption over a move or
    a held proxy guard. Conditions preceding acceptance are not simulated.
    """
    skills = [{'name': s['name'], 'blocks': bs} for s, bs in zip(source.skills, source.blocks)]
    result = {}
    for name, description in identify(skills).items():
        result[name] = {}
        for action, data in description['actions'].items():
            origin = data['command']
            command = source.blocks[origin['skill']][origin['block']]
            target, at = command[2:4]
            deductions = []
            for i in range(at, len(source.blocks[target])):
                b = source.blocks[target][i]
                if b[0] == 'V' and b[1:4] == [71, 2, 0]:
                    deductions.append({'skill': target, 'block': i, 'delta': b[4]})
                if b[0] in ('SG', 'E'):
                    break
            result[name][action] = deductions
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('json_dir', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(args.json_dir.glob('*.json'))
    yp = next(p for p in paths if official(p.stem) == 'ゆい')
    base = Source(yp)
    starts = [base.names[n][0] for n in STARTS.values()] + [base.names['kage2  '][0]]
    groups = {name: list(range(starts[i], starts[i+1])) + [base.names[SUPPORTS[name][2]][0]]
              for i, name in enumerate(SUPPORTS)}
    ids = [n for g in groups.values() for n in g]
    results = {'basis': 'Yui; source JSON, inactive V operands removed, media contents and aligned targets compared',
               'limitations': ['Not a proof of behavioral equivalence; reachability/conditions are not simulated.',
                               'Indexed media identity excludes global palette colors.',
                               'Unmatched destinations remain explicit; helper bodies require a separate comparison.'],
               'base_sha256': base.sha256, 'base_action_costs': action_costs(base), 'characters': []}
    for p in paths:
        if p == yp:
            continue
        owner = Source(p)
        rows = compare(base, owner, ids)
        for row in rows:
            row['support'] = next(s for s, ns in groups.items() if row['id'] in ns)
        pairs = pair_skills(base, owner)
        external = {b[k] for n in ids for b in base.blocks[n] for k in ref_positions(b)
                    if b[k] > 0 and b[k] not in ids}
        owner_ids = {pairs[n] for n in ids if n in pairs}
        owner_external = {b[k] for n in owner_ids for b in owner.blocks[n] for k in ref_positions(b)
                          if b[k] > 0 and b[k] not in owner_ids}
        result = {'character': owner.name, 'source_sha256': owner.sha256,
                  'action_costs': action_costs(owner), 'skills': rows,
                  'direct_helper_differences': compare(base, owner, sorted(external)),
                  'additional_helper_targets': [{'id': n, 'name': owner.skills[n]['name']}
                                               for n in sorted(owner_external - {pairs[n] for n in external if n in pairs})]}
        results['characters'].append(result)
        print(owner.name, len(rows), 'support definitions differ', flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
