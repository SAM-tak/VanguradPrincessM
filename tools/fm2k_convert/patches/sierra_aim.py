"""Port-specific 6D: preserve the direction selected by the aiming pose."""
from copy import deepcopy


def patch_package(entries):
    def find(name):
        matches = [(n, sk) for n, sk in entries if sk['name'] == name]
        if len(matches) != 1:
            raise ValueError(f'Sierra patch: expected one {name}')
        return matches[0]

    aim_id, aim = find('待機')
    shot_id, shot = find('サポートショット')

    def direction_split(skill, number):
        matches = [(i, b) for i, b in enumerate(skill['blocks'])
                   if b[:7] == ['V', 75, 0, 0, 0, 1, 1] and b[7] == number]
        if len(matches) != 1:
            raise ValueError('Sierra patch: direction branch changed')
        return matches[0]

    _, aim_branch = direction_split(aim, aim_id)
    shot_index, shot_branch = direction_split(shot, shot_id)
    # A private normal-facing entry repeats the colour initialization but
    # skips V75. Keep every original offset, including 5D's entry, intact.
    prefix = shot['blocks'][1:shot_index]
    if prefix != [['COLOR', 0, 0, 0, 0, 0]]:
        raise ValueError('Sierra patch: shot initialization changed')
    if shot['blocks'][shot_branch[8]] != prefix[0] or shot['blocks'][-1][0] not in ('SG', 'E'):
        raise ValueError('Sierra patch: shot entry/exit changed')
    normal = len(shot['blocks'])
    counts = [0, 0]
    for i, block in enumerate(aim['blocks']):
        target = 7 if block[0] == 'V' else 1 if block[0] == 'SG' else None
        if target is not None and block[target] == shot_id:
            if block[0] == 'V' and block[:7] != ['V', 76, 0, 0, 0, 1, 101]:
                raise ValueError('Sierra patch: unexpected early-fire condition')
            if block[target + 1] != 0:
                raise ValueError('Sierra patch: unexpected shot entry')
            side = int(i >= aim_branch[8])
            block[target + 1] = shot_branch[8] if side else normal
            counts[side] += 1
    if not all(counts):
        raise ValueError('Sierra patch: missing aim-to-shot transitions')
    shot['blocks'].extend(deepcopy(prefix) + [['SG', shot_id, shot_index + 1]])
