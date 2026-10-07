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
    parser.add_argument('--player-dir', type=Path, help='restore DB/FA omitted by the JSON parser from matching .player files')
    parser.add_argument('--out', type=Path, default=ROOT / 'build/fm2k-vm-audit.json')
    args = parser.parse_args()
    blocks = list(inventory(args.data))
    ops = Counter(b['instruction'][0] for b in blocks)
    flags, events = Counter(), Counter()
    color_modes, color_values = Counter(), [Counter() for _ in range(4)]
    gaps = defaultdict(list)
    handled = defaultdict(list)
    for row in blocks:
        b = row['instruction']
        op = b[0]
        if op == 'COLOR':
            color_modes[b[1]] += 1
            for values, value in zip(color_values, b[2:6]):
                values[value] += 1
            if b[1] not in range(5) or any(not -32 <= (n - 256 if n >= 128 else n) <= 32 for n in b[2:5]) or (b[1] == 4 and not 0 <= b[5] <= 32):
                gaps['COLOR_outside_reviewed_range'].append(row)
        if isinstance(b[-1], str) and len(b) > 1:
            for flag in b[-1].split():
                flags[f'{op}.{flag}'] += 1
        if op == 'DS' and b[1] >= 0:
            events[b[-1]] += 1
            if b[-1] == 'whileThrowDo':
                handled['DS_throw_contact'].append(row)
            elif b[-1] == 'offsetWay':
                handled['DS_FA_contact'].append(row)
        if op in ('GL', 'GS') and b[3 if op == 'GL' else 4] <= 0:
            gaps['gauge_zero_target_fallback'].append(row)
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
                handled['O_occupied_slot_branch'].append(row)
            if 'shadow' in b[-1].split():
                gaps['O_shadow_flag_ignored'].append(row)
            if b[1] == 0:
                handled['O_zero_skill_delete'].append(row)
        if op == 'FA' and 'halfed' in b[-1].split():
            handled['FA_guard_chip'].append(row)
        if op == 'FD' and 'throw' in b[-1].split():
            handled['FD_throw_contact'].append(row)
        if op == 'RP' and set(b[-1].split()) & {'in', 'out'}:
            handled['RP_depth_flags'].append(row)
        if op == 'COM':
            handled['COM_history_window'].append(row)
        if op == 'DB':
            handled['DB_basic_condition'].append(row)
        if op == 'V' and b[2] == 2:
            handled['V_add_saturation'].append(row)
    sound_options = Counter()
    for path in sorted(args.data.rglob('sounds.lton')):
        if '_conversion' in path.parts:
            continue
        for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            match = re.search(r'type = (\d+).*endlessLoop = (true|false)\^, cddaTrack = (\d+)', line)
            if not match:
                continue
            kind, loop, track = match.groups()
            sound_options[f'type={kind},loop={loop},cdda={track}'] += 1
            if kind not in ('0', '1') or track != '0':
                gaps['sound_unreviewed_options'].append(dict(file=path.relative_to(ROOT).as_posix(), line=line_no, text=line.strip()))
    raw_ops, lost = Counter(), []
    color_alpha_flags = Counter()
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
        from gen_script import block as convert_block, restore_fa_flags
        for path in sorted(args.json_dir.glob('*.json')):
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if args.player_dir:
                restore_fa_flags(args.player_dir / (path.stem + '.player'), data)
            for n, skill in enumerate(data.get('skills', [])):
                for i, b in enumerate(skill['blocks']):
                    raw_ops[b['type']] += 1
                    if b['type'] == 'COLOR':
                        color_alpha_flags[f"mode={b['option']},aEnabled={b['aEnabled']}"] += 1
                    if convert_block(b)[0] == 'Nop':
                        row = dict(file=str(path), skill=n, name=skill['name'], block=i, raw=b)
                        if b['type'] == 'DS' and b['when'] == 0:
                            handled['DS_zero_original_noop'].append(row)
                        else:
                            lost.append(row)
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
    result['render_sound_inventory'] = dict(
        color_modes=dict(color_modes),
        color_operands={key: dict(sorted(values.items())) for key, values in zip(('r', 'g', 'b', 'a'), color_values)},
        raw_color_alpha_flags=dict(color_alpha_flags), sound_options=dict(sound_options))
    # A zero missing_dispatch count does not mean complete FM2K compatibility.
    result['runtime_reviews'] = [
        'Used render pixel blending/layer behavior and sound playback semantics (COLOR operand range and sound metadata inventoried in 0098)',
    ]
    result['out_of_scope_unused'] = [
        'RC nonzero common-pose binding', 'EB nonzero colour fades', 'O shadow rendering flag',
        'GL/GS zero-target command fallback (no current definitions; inventoried if introduced)',
    ]
    dispatch = set(re.findall(r'op = "([A-Za-z]+)"', (ROOT / 'src/script.lh').read_text(encoding='utf-8')))
    result['missing_dispatch'] = {op: count for op, count in ops.items() if op not in dispatch and op != 'Nop'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('files', 'blocks', 'operations', 'registered_events')}, ensure_ascii=False))
    print(json.dumps({k: len(v) for k, v in gaps.items()}, ensure_ascii=False))
    print(f'Conversion Nops: {len(lost)}; report: {args.out}')


if __name__ == '__main__':
    main()
