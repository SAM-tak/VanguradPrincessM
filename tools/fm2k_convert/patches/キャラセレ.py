"""The character select screen's curtain goes in front of the cursors.

Layer #31 (スクリプト1) is a fade-in: it draws the background (image 0) over
everything, from black (COLOR 224 = -32) up to as is, then fades it out. It
comes after the system-image marker (#16), so it sits at depth 100: above the
portraits (80), below the cursors (101) and the support arrows (127), which
show through the black. The original does the same, too briefly to see
(TechnicalDocuments/0019).

Changed: the curtain's blocks move to the unused skill #32, which #31 runs as
an object at depth 127 ("point"). Spawned after the screen's other objects, it
draws over the arrows at 127 too. #32 keeps its empty name, so it is not a
layer of its own.
"""

from patches import renumber

CURTAIN = 31
SLOT = 32
DEPTH = 127


def patch(d):
    skills = d["skills"]
    curtain, slot = skills[CURTAIN], skills[SLOT]
    assert curtain["name"] == "スクリプト1" and slot["name"] == "" and not slot["blocks"], \
        "キャラセレ: skills 31 / 32 are not what this patch expects"
    settings, body = curtain["blocks"][0], curtain["blocks"][1:]
    assert settings["type"] == "Settings"

    slot["blocks"] = [dict(settings)] + body
    renumber(slot["blocks"])

    spawn = {
        "in": False, "out": False, "point": True, "unCond": True, "shadow": False,
        "parent": False, "picXY": True,
        "skill": {"block": 0, "blockType": "Settings", "name": "", "number": SLOT},
        "outSkill": {"block": 0, "blockType": "I", "name": "－－設定無し－－", "number": 0},
        "x": 0, "y": 0, "number": 0, "depth": DEPTH, "depthEnabled": True, "type": "O",
    }
    curtain["blocks"] = [settings, spawn, {"type": "E"}]
    renumber(curtain["blocks"])
