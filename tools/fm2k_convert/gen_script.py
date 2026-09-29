"""Write a character's (stage's, the system's) FM2K skills as compact LTON for
src/script.lh to run: script.lton next to the converted assets.

Each skill is { name, level, blocks = { block, ... } }, its position the skill
number. A block is a positional list: its type, then numbers, then at most one
string (flags or an event name). Jumps are (skill, block) pairs; skill -1 is
"none". The layouts per type are the table in TechnicalDocuments/0012 and
src/script.lh; they follow what gen_skills.py wrote as L^ calls.

The character's command table, hit reactions (hit-junction table) and gauge
settings go in the same file.

usage: gen_script.py <fm2ndparser json> <asset dir> [--layers]
"""

import argparse
import json
import struct
from pathlib import Path

from gen_skills import DS_EVENTS, flags, steps_of, target

CMP = {"itsTheSame": 1, "itsAbove": 2, "itsBelow": 3}


def ref(r):
    t = target(r)
    return list(t) if t else [-1, 0]


def lton_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def block(b):
    """One block as [type, numbers..., string?]."""
    t = b["type"]
    if t == "Settings":
        if b.get("settingsType") == 6:     # a stage layer: scroll ratios and loops
            return ["Layer", b["width"], b["height"], flags(
                b, ["widthEnabled", "heightEnabled", "connectLtRt", "connectUpDw"],
                {"widthEnabled": "scrollX", "heightEnabled": "scrollY", "connectLtRt": "loopX", "connectUpDw": "loopY"})]
        return ["Settings", b["level"], b.get("time", 0)]    # time: a system skill's show time
    if t == "I":
        return ["I", b["i"], b["wait"], b["x"], b["y"], flags(b, ["turnX", "turnY", "ignoreDirection"])]
    if t == "FD":
        return ["FD", b["number"], b["x"], b["y"], b["width"], b["height"], b["damageRate"],
                flags(b, ["damaged", "collide", "throw"])]
    if t == "FA":
        return ["FA", b["number"], b["x"], b["y"], b["width"], b["height"], b["power"],
                flags(b, ["cancel", "noDetection", "combo", "noSkyDetection", "guardFail", "duringGuard",
                          "duringReceipt", "halfed"])]
    if t == "M":
        return ["M", b["moveX"], b["moveY"], b["gravityX"], b["gravityY"],
                flags(b, ["add", "stopMoveX", "stopMoveY", "stopGravityX", "stopGravityY"],
                      {"stopMoveX": "keepVX", "stopMoveY": "keepVY", "stopGravityX": "keepAX", "stopGravityY": "keepAY"})]
    if t == "S":
        return ["S", b["sound"]["number"]]
    if t == "E":
        return ["E"]
    if t == "SG":
        return ["SG"] + ref(b["skill"])
    if t in ("SC", "SF"):
        return [t] + ref(b["skill"]) + [b.get("loop", 1) if t == "SF" else 1]
    if t == "V":
        mode = 1 if b["replace"] else 2 if b["add"] else 0
        cmp = next((v for k, v in CMP.items() if b[k]), 0)
        return ["V", b["var"], mode, 1 if b["useEven"] else 0, b["useEvenVar"] if b["useEven"] else b["value"],
                cmp, b["multiCondValue"]] + ref(b["multiCondSkill"])
    if t == "Rnd":
        return ["Rnd", b["randomNum"], b["whenItsAbove"]] + ref(b["skill"])
    if t == "COM":
        dirs, buttons = steps_of(b["steps"])
        d = json.loads(dirs.replace("{", "[").replace("}", "]"))
        k = json.loads(buttons.replace("{", "[").replace("}", "]"))
        return ["COM", b["time"]] + ref(b["skill"]) + [len(d)] + d + k
    if t == "GL":
        return ["GL", 1 if b["isMore"] else 0, b["add"]] + ref(b["skill"])
    if t == "GS":
        return ["GS", b["level"], 1 if b["isMore"] else 0, b["add"]] + ref(b["skill"])
    if t == "DS":
        if b["when"] not in DS_EVENTS:
            return ["Nop"]
        return ["DS"] + ref(b["skill"]) + [DS_EVENTS[b["when"]]]
    if t == "O":
        r = target(b["skill"]) or (0, 0)
        out = target(b["outSkill"]) or (0, 0)
        return ["O", r[0], r[1], b["x"], b["y"], b["number"], b["depth"], out[0], out[1],
                flags(b, ["out", "point", "unCond", "shadow", "parent", "picXY"])]
    if t == "C":
        when = "hits" if b["hits"] else "uncond" if b["uncond"] else "fails"
        return ["C", b["from"], b["to"], b["skill"]["number"] if b["skillCancelCondition"] else -1, when]
    if t == "R":
        keys = ["hitsStand", "hitsCrouched", "hitsAir", "guardStand", "guardCrouched", "guardAir"]
        return ["R"] + [b[k]["number"] for k in keys]
    if t == "PS":
        return ["PS", b["playerTime"], b["enemyTime"]]
    if t == "GP":
        return ["GP", b["playerLifeGauge"], b["playerSpecialGauge"], b["enemyLifeGauge"], b["enemySpecialGauge"]]
    if t == "EB":
        c = b["rgba"]
        return ["EB", b["fadingType"], c["r"], c["g"], c["b"], c["a"], b["duration"],
                flags(b, ["player", "enemy", "bg", "system"])]
    if t == "AI":
        c = b["rgba"]
        return ["AI", b["num"], b["time"], b["option"], b["fadingType"], c["r"], c["g"], c["b"], c["a"]]
    if t == "COLOR":
        c = b["rgba"]
        return ["COLOR", b["option"], c["r"], c["g"], c["b"], c["a"]]
    if t == "RC":
        return ["RC", b["commonImage"]["number"], b["x"], b["y"], flags(b, ["in", "turnX", "turnY", "same"])]
    if t == "RP":
        return ["RP", b["hitJunction"]["number"], b["x"], b["y"], flags(b, ["in", "out", "turnX"])]
    return ["Nop"]


def raw_command_steps(player, commands):
    """Each command's steps as (mode, amount) for its active steps, read from
    the .player file itself: fm2ndparser drops the step's mode bits (0xC000 of
    the 16-bit step mask: 0 press, 0x4000 repeat, 0x8000 charge, both turn =
    a rotation). Layout: wanwan docs/editor/player_file_format.md, block 4
    (82-byte entries: name[32], time, 4 skills, 10 masks, 10 amounts)."""
    b = player.read_bytes()
    names = [c["name"].encode("cp932") for c in commands]
    if not names:
        return []
    start = b.find(names[0] + b"\0")
    while start >= 0:
        if all(b[start + 82 * k:start + 82 * k + len(n) + 1] == n + b"\0" for k, n in enumerate(names)):
            break
        start = b.find(names[0] + b"\0", start + 1)
    if start < 0:
        raise SystemExit("commands not found in %s" % player)
    out = []
    for k in range(len(commands)):
        e = b[start + 82 * k:start + 82 * k + 82]
        masks = struct.unpack("<10H", e[42:62])
        amounts = struct.unpack("<10H", e[62:82])
        out.append([(m >> 14, a) for m, a in zip(masks, amounts) if m & 0x2000])
    return out


def lton_list(items):
    return "{ " + ", ".join(lton_str(x) if isinstance(x, str) else str(x) for x in items) + " }"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", type=Path)
    ap.add_argument("out", type=Path, help="the converted asset folder, e.g. assets/characters/ゆい")
    ap.add_argument("--player", type=Path, default=None,
                    help="the character's .player file, for the command steps' modes (rotation, charge)")
    ap.add_argument("--layers", action="store_true",
                    help="a script that ends with E hides its image (stages, the system file's HUD scripts)")
    args = ap.parse_args()

    d = json.loads(args.json.read_text(encoding="utf-8-sig"))
    skills = d["skills"]
    lines = ["# Converted from %s by tools/fm2k_convert/gen_script.py; run by src/script.lh." % args.json.name,
             "# Position = skill number. Block layouts: TechnicalDocuments/0012.",
             "layers = %s," % ("true^" if args.layers else "false^")]

    if "settings" in d:
        st = d["settings"]
        lines.append("settings = { lifeMax = %d, specialPer = %d, stockMax = %d, startStock = %d },"
                     % (st["lifeGaugeMax"], st["specialGaugeMax"], st["specialMaxStock"], st["startStock"]))
    # Reaction number (the attacker's R block) -> this character's hit skill and spark.
    reactions = []
    for i, r in enumerate(d.get("hitJunctionsSkills", [])):
        hit, spark = r["hitJunction"]["number"], r["spark"]["number"]
        if hit or spark:
            reactions.append([i, hit, spark])
    if reactions:
        lines.append("reactions = {")
        lines += ["    %s," % lton_list(r) for r in reactions]
        lines.append("},")
    commands = []
    raw = raw_command_steps(args.player, d.get("commands", [])) if args.player else []
    for ci, c in enumerate(d.get("commands", [])):
        dirs, buttons = steps_of(c["steps"])
        dl = json.loads(dirs.replace("{", "[").replace("}", "]"))
        bl = json.loads(buttons.replace("{", "[").replace("}", "]"))
        refs = [c[k]["number"] for k in ("airSkill", "standSkill", "standFarSkill", "crouchedSkill")]
        if not any(refs) or not any(bl) and all(x == 0 for x in dl):
            continue
        steps = raw[ci] if ci < len(raw) else [(0, 1)] * len(dl)
        modes = [m for m, _ in steps]
        amounts = [a for _, a in steps]
        commands.append("    { name = %s, time = %d, skills = %s, directions = %s, buttons = %s, modes = %s, amounts = %s },"
                        % (lton_str(c["name"]), c["time"], lton_list(refs), lton_list(dl), lton_list(bl),
                           lton_list(modes), lton_list(amounts)))
    if commands:
        lines.append("commands = {")
        lines += commands
        lines.append("},")

    for n, sk in enumerate(skills):
        bs = sk["blocks"]
        lv = bs[0].get("level", 0) if bs and bs[0]["type"] == "Settings" else 0
        lines.append("{ name = %s, level = %d, blocks = {" % (lton_str(sk["name"]), lv))
        lines += ["    %s," % lton_list(block(b)) for b in bs]
        lines.append("} },")

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "script.lton").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("%d skills -> %s" % (len(skills), args.out / "script.lton"))


if __name__ == "__main__":
    main()
