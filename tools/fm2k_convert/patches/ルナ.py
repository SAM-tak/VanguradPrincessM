"""Leave Luna's stance wait loops after the system announces KO.

Append branch trampolines so every original block reference stays valid.
Attack startup and active frames are unchanged.
"""
from copy import deepcopy
from patches import renumber

# skill: (loop-back instruction, wait-loop entry)
LOOPS = {228: (180, 44), 230: (190, 48), 232: (209, 73),
         234: (191, 55), 236: (159, 53), 238: (203, 60),
         241: (187, 68), 246: (211, 67)}


def patch(d):
    skills = d['skills']
    assert skills[240]['name'] == '終了', 'Luna stance exit changed'
    template = next(b for b in skills[236]['blocks']
                    if b['type'] == 'V' and b['var'] == 138)
    for number, (at, entry) in LOOPS.items():
        blocks = skills[number]['blocks']
        original = deepcopy(blocks[at])
        assert original['type'] == 'SG' and original['skill']['number'] == number
        assert original['skill']['block'] == entry, 'Luna wait loop changed'
        check = deepcopy(template)
        check['multiCondSkill'] = dict(number=240, block=0,
                                      name='終了', blockType='Settings')
        blocks[at]['skill'] = dict(number=number, block=len(blocks),
                                  name=skills[number]['name'], blockType='V')
        blocks.extend([check, original])
        renumber(blocks)
