"""Inventory emitted FM2K blocks and known runtime gaps without changing data.

This reads the converter's one-line block format, not arbitrary LTON. Counts
are stored definitions, not execution frequency or proof of reachability.
Optional parser JSON input also identifies blocks discarded by conversion.
Run from the project root: python tools/fm2k_convert/audit_vm.py
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def inventory(root):
    for path in sorted(root.rglob('*.lton')):
        if '_conversion' in path.parts:
            continue
        skill, name, index = None, '', 0
        for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            match = re.search(r'\{ name = "(.*?)", level = .*?id = (-?\d+),', line)
            if match:
                name, skill, index = match[1], int(match[2]), 0
            if not re.match(r'^\s*\{ "[A-Za-z]+"(?:,|\s*})', line):
                continue
            text = line.strip().removesuffix(',')
            block = json.loads('[' + text[1:-1] + ']')
            yield dict(file=path.relative_to(ROOT).as_posix(), line=line_no,
                       skill=skill, name=name, block=index, instruction=block)
            index += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--json-dir', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/fm2k-vm-audit.json')
    args = parser.parse_args()
    blocks = list(inventory(args.data))
    ops = Counter(b['instruction'][0] for b in blocks)
    flags, events = Counter(), Counter()
    gaps = defaultdict(list)
    handled = defaultdict(list)
    for row in blocks:
        b = row['instruction']
        op = b[0]
        if isinstance(b[-1], str) and len(b) > 1:
            for flag in b[-1].split():
                flags[f'{op}.{flag}'] += 1
        if op == 'DS' and b[1] >= 0:
            events[b[-1]] += 1
            if b[-1] in ('offsetWay', 'whileThrowDo'):
                gaps['event_never_fired'].append(row)
        if op == 'Nop':
            gaps['Nop_origin_review_not_necessarily_missing'].append(row)
        if op in ('AI', 'RC'):
            # Zero-count AI is a disable instruction; report separately.
            if op == 'AI':
                handled['AI_active' if b[1] > 0 else 'AI_disable'].append(row)
            elif b[1] == 0:
                handled['RC_zero_original_noop'].append(row)
            else:
                gaps['RC_nonzero_not_implemented'].append(row)
        if op == 'EB' and any(b[1:7]):
            if b[1] == 0:
                handled['EB_colour_disabled_by_mode_zero'].append(row)
            else:
                gaps['EB_colour_fade_ignored'].append(row)
        if op == 'O':
            if b[7] > 0:
                gaps['O_outSkill_ignored'].append(row)
            if 'shadow' in b[-1].split():
                gaps['O_shadow_flag_ignored'].append(row)
            if b[1] == 0:
                gaps['O_zero_skill_early_return_review'].append(row)
        if op == 'FA' and 'halfed' in b[-1].split():
            gaps['FA_halfed_ignored'].append(row)
        if op == 'FD' and 'throw' in b[-1].split():
            gaps['FD_throw_flag_not_tested'].append(row)
        if op == 'RP' and set(b[-1].split()) & {'in', 'out'}:
            handled['RP_depth_flags'].append(row)
        if op == 'COM':
            gaps['COM_polling_window_review'].append(row)
        if op == 'V' and b[2] == 2:
            handled['V_add_saturation'].append(row)
    raw_ops, lost = Counter(), []
    commands = defaultdict(list)
    for path in sorted((args.data / 'characters').glob('*/script.lton')):
        for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            if 'directions =' not in line:
                continue
            row = dict(file=path.relative_to(ROOT).as_posix(), line=line_no, text=line.strip())
            skills = re.search(r'skills = \{([^}]+)', line)
            modes = re.search(r'modes = \{([^}]+)', line)
            if skills:
                values = [int(n) for n in skills[1].split(',')]
                if values[1] != values[2]:
                    commands['far_stand_differ'].append(row)
            if modes and any(int(n) in (1, 2) for n in modes[1].split(',')):
                commands['repeat_charge_mode'].append(row)
    if args.json_dir:
        from gen_script import block as convert_block
        for path in sorted(args.json_dir.glob('*.json')):
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            for n, skill in enumerate(data.get('skills', [])):
                for i, b in enumerate(skill['blocks']):
                    raw_ops[b['type']] += 1
                    if convert_block(b)[0] == 'Nop':
                        lost.append(dict(file=str(path), skill=n, name=skill['name'], block=i, raw=b))
    source_hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                     for p in ['src/fighter.lh', 'src/afterimage.lh', 'src/script.lh', 'main.lh',
                               'tools/fm2k_convert/gen_script.py']}
    result = dict(scope='Emitted data except _conversion; static definitions, reachability not inferred',
                  files=len({b['file'] for b in blocks}), blocks=len(blocks),
                  handled_sites=dict(handled),
                  operations=dict(ops.most_common()), flags=dict(flags.most_common()),
                  registered_events=dict(events),
                  findings={k: dict(count=len(v), locations=v) for k, v in gaps.items()},
                  raw_operations=dict(raw_ops), conversion_nops=lost, source_sha256=source_hashes,
                  command_findings=dict(commands))
    dispatch = set(re.findall(r'op = "([A-Za-z]+)"', (ROOT / 'src/script.lh').read_text(encoding='utf-8')))
    result['missing_dispatch'] = {op: count for op, count in ops.items() if op not in dispatch and op != 'Nop'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('files', 'blocks', 'operations', 'registered_events')}, ensure_ascii=False))
    print(json.dumps({k: len(v) for k, v in gaps.items()}, ensure_ascii=False))
    print(f'Conversion Nops: {len(lost)}; report: {args.out}')


if __name__ == '__main__':
    main()
