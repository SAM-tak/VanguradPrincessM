"""Generate L^ skill procedures from a character's FM2K blocks — drafts for
rewriting a skill by hand. The game itself runs the skills from data
(gen_script.py, src/script.lh, TechnicalDocuments/0012).

Each skill becomes `p^me:Fighter, at:number^` (at = block to start at) in
src/chara/<id>/skills/sNNNN.lh, 100 skills per file, plus skills.lh that puts
them into the fighter's table. The vocabulary is src/fighter.lh; the design is
TechnicalDocuments/0005.

Jumps inside a skill become structured where that is trivial (a skill whose
only target is its own start is a `repeat^` loop) and a `pc` dispatch loop
otherwise. Jumps to other skills become `me.jump(...)` + `return^`; calls become
`await^me.call(...)`. The output is a draft to be edited, not a build artefact.

usage: gen_skills.py <fm2ndparser json> <id> [--out src/chara]
"""

import argparse
import json
from pathlib import Path

PER_FILE = 100

CONDITIONAL = ("Rnd", "COM", "GL", "GS", "V", "DB")
DS_EVENTS = {1: "landing", 2: "attacking", 3: "defending", 4: "wallHitting", 5: "offsetWay", 6: "whileThrowDo"}
DIRECTIONS = ["Free", "Point", "Right", "DownRight", "Down", "DownLeft", "Left", "UpLeft", "Up", "UpRight",
              "UpLeftDown", "UpLeftRight", "UpRightDown", "DownLeftRight"]
VAR_NAMES = {**{n: "task %s" % chr(65 + n) for n in range(17)},
             **{64 + n: "char %s" % chr(65 + n) for n in range(16)},
             **{128 + n: "system %s" % chr(65 + n) for n in range(16)},
             192: "x", 193: "y", 194: "map x", 195: "map y", 196: "parent x", 197: "parent y",
             198: "time", 199: "rounds"}


def target(ref):
    """(skill, block) a reference points at, or None for "none" (skill 0)."""
    if not ref or ref.get("number", 0) == 0:
        return None
    return ref["number"], ref.get("block", 0)


def jump_refs(b):
    """Every (skill, block) a block can transfer control to or start."""
    t = b["type"]
    keys = {"SG": ["skill"], "SC": ["skill"], "SF": ["skill"], "Rnd": ["skill"], "COM": ["skill"],
            "GL": ["skill"], "GS": ["skill"], "DS": ["skill"], "V": ["multiCondSkill"],
            "O": ["skill", "outSkill"], "DB": ["skill"]}.get(t, [])
    out = [target(b.get(k)) for k in keys]
    if t == "V" and not (b["itsTheSame"] or b["itsAbove"] or b["itsBelow"]):
        out = []
    return [x for x in out if x]


BUTTONS = "abcdef"


def steps_of(steps):
    """Active input steps as two L^ lists: FM2K direction codes and button bitmasks
    (a = 1, b = 2, ... f = 32)."""
    active = [s for s in steps if s["active"]]
    dirs = [s["direction"] for s in active]
    buttons = [sum(1 << k for k, c in enumerate(BUTTONS) if s[c]) for s in active]
    return "{ %s }" % ", ".join(map(str, dirs)), "{ %s }" % ", ".join(map(str, buttons))


def flags(b, names, rename=None):
    rename = rename or {}
    return " ".join(rename.get(n, n) for n in names if b.get(n))


def q(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


class SkillWriter:
    stage = False       # writing layer scripts (a stage's, the system's HUD): E hides the image

    def __init__(self, number, skill, entries):
        self.n = number
        self.skill = skill
        self.blocks = skill["blocks"]
        local = {b for blk in self.blocks for (s, b) in jump_refs(blk) if s == number and blk["type"] in
                 ("SG", "Rnd", "COM", "GL", "GS", "V")}
        self.labels = sorted(({0} | local | entries.get(number, set())) & set(range(len(self.blocks))) | {0})
        self.dispatch = self.labels != [0]
        if self.dispatch:
            # lhat leaks registers on next^ inside if^ (about 60 per loop), so the
            # dispatch loop never uses it: a conditional jump sets pc and ends its
            # segment, and what follows becomes a segment of its own.
            after = {i + 1 for i, blk in enumerate(self.blocks)
                     if blk["type"] in CONDITIONAL and any(s == number for s, _ in jump_refs(blk))}
            self.labels = sorted(set(self.labels) | {i for i in after if i < len(self.blocks)})
        self.here = 0
        self.loops = any(s == number and b == 0 for blk in self.blocks for (s, b) in jump_refs(blk)
                         if blk["type"] in ("SG", "Rnd", "COM", "GL", "GS", "V"))

    # -- control transfer -------------------------------------------------
    def goto(self, ref):
        n, b = ref
        if n == self.n and b >= len(self.blocks):
            return ["return^"]          # past the last block: the skill ends
        if n == self.n:
            if self.dispatch:
                return ["pc := %d" % b]
            return ["next^"]
        return ["me.jump(%d, %d)" % (n, b), "return^"]

    def branch(self, cond, ref):
        if self.dispatch and ref[0] == self.n:
            nxt = self.here + 1 if self.here + 1 < len(self.blocks) else -1
            to = ref[1] if ref[1] < len(self.blocks) else -1     # past the end: finish
            return ["pc := %d" % nxt, "if^%s { pc := %d }" % (cond, to)]
        return ["if^%s {" % cond] + ["    " + s for s in self.goto(ref)] + ["}"]

    # -- one block -> (lines, ends_flow) -----------------------------------
    def block(self, i, b):
        t = b["type"]
        if t == "Settings":
            if b.get("settingsType") == 6:     # a stage layer: scroll ratios and loops
                return ["me.layer(%d, %d, %s)" % (b["width"], b["height"], q(flags(
                    b, ["widthEnabled", "heightEnabled", "connectLtRt", "connectUpDw"],
                    {"widthEnabled": "scrollX", "heightEnabled": "scrollY", "connectLtRt": "loopX", "connectUpDw": "loopY"})))], False
            return ["me.settings(%d)" % b["level"]], False
        if t == "I":
            f = flags(b, ["turnX", "turnY", "ignoreDirection"])
            if f:
                return ["await^me.showEx(%d, %d, %d, %d, %s)" % (b["i"], b["wait"], b["x"], b["y"], q(f))], False
            return ["await^me.show(%d, %d, %d, %d)" % (b["i"], b["wait"], b["x"], b["y"])], False
        if t == "FD":
            if b["width"] == 0 and b["height"] == 0:
                return ["me.noHurt(%d)" % b["number"]], False
            f = flags(b, ["damaged", "collide", "throw"])
            args = (b["number"], b["x"], b["y"], b["width"], b["height"])
            if b["damageRate"] == 100 and f == "damaged":
                return ["me.hurt(%d, %d, %d, %d, %d)" % args], False
            if b["damageRate"] == 100 and f == "collide":
                return ["me.body(%d, %d, %d, %d, %d)" % args], False
            return ["me.fd(%d, %d, %d, %d, %d, %s, %d)" % (args + (q(f), b["damageRate"]))], False
        if t == "FA":
            if b["width"] == 0 and b["height"] == 0:
                return ["me.noHit(%d)" % b["number"]], False
            f = flags(b, ["cancel", "noDetection", "combo", "noSkyDetection", "guardFail", "duringGuard",
                          "duringReceipt", "halfed", "projectileCancel"])
            args = (b["number"], b["x"], b["y"], b["width"], b["height"], b["power"])
            if not f:
                return ["me.hit(%d, %d, %d, %d, %d, %d)" % args], False
            return ["me.fa(%d, %d, %d, %d, %d, %d, %s)" % (args + (q(f),))], False
        if t == "M":
            f = flags(b, ["add", "stopMoveX", "stopMoveY", "stopGravityX", "stopGravityY"],
                      {"stopMoveX": "keepVX", "stopMoveY": "keepVY", "stopGravityX": "keepAX", "stopGravityY": "keepAY"})
            return ["me.motion(%d, %d, %d, %d, %s)" % (b["moveX"], b["moveY"], b["gravityX"], b["gravityY"], q(f))], False
        if t == "S":
            return ["me.sound(%d)" % b["sound"]["number"]], False
        if t == "E":
            # A stage layer that ends with E is gone; one that runs past its
            # last block keeps showing its last image.
            return (["me.vanish()"] if SkillWriter.stage else []) + ["return^"], True
        if t == "SG":
            ref = target(b["skill"])
            return (self.goto(ref), True) if ref else (["# SG to nothing"], False)
        if t in ("SC", "SF"):
            ref = target(b["skill"])
            if not ref:
                return ["# %s to nothing" % t], False
            line = "await^me.call(%d, %d)" % ref
            if t == "SC":
                return [line], False
            return ["for^k from^1 to^%d {" % b["loop"], "    " + line, "}"], False
        if t == "V":
            lines = []
            operand = "me.v(%d)" % b["useEvenVar"] if b["useEven"] else "%d" % b["value"]
            name = VAR_NAMES.get(b["var"], "?")
            if b["replace"]:
                lines.append("me.setv(%d, %s)    # %s" % (b["var"], operand, name))
            elif b["add"]:
                lines.append("me.addv(%d, %s)    # %s" % (b["var"], operand, name))
            op = "=" if b["itsTheSame"] else ">" if b["itsAbove"] else "<" if b["itsBelow"] else None
            ref = target(b["multiCondSkill"])
            if op and ref:
                lines += self.branch("me.v(%d) %s %d" % (b["var"], op, b["multiCondValue"]), ref)
            return lines or ["# V: nothing"], False
        if t == "Rnd":
            ref = target(b["skill"])
            if not ref:
                return ["# Rnd to nothing"], False
            return self.branch("me.chance(%d, %d)" % (b["randomNum"], b["whenItsAbove"]), ref), False
        if t == "COM":
            ref = target(b["skill"])
            if not ref:
                return ["# COM to nothing"], False
            dirs, buttons = steps_of(b["steps"])
            return self.branch("me.command(%d, %s, %s)" % (b["time"], dirs, buttons), ref), False
        if t == "GL":
            ref = target(b["skill"])
            cond = "me.lifeGauge(%s, %d)" % ("true^" if b["isMore"] else "false^", b["add"])
            return (self.branch(cond, ref) if ref else ["# GL to nothing"]), False
        if t == "GS":
            ref = target(b["skill"])
            cond = "me.specialGauge(%d, %s, %d)" % (b["level"], "true^" if b["isMore"] else "false^", b["add"])
            return (self.branch(cond, ref) if ref else ["# GS to nothing"]), False
        if t == "DS":
            ref = target(b["skill"])
            if b["when"] not in DS_EVENTS:
                return ["# DS: nothing"], False
            if not ref:
                return ["me.off(%s)" % q(DS_EVENTS[b["when"]])], False
            return ["me.on(%s, %d, %d)" % ((q(DS_EVENTS[b["when"]]),) + ref)], False
        if t == "O":
            ref = target(b["skill"]) or (0, 0)
            out = target(b["outSkill"]) or (0, 0)
            f = flags(b, ["out", "point", "unCond", "shadow", "parent", "picXY"])
            call = "me.spawn(%d, %d, %d, %d, %d, %d, %d, %d, %s)" % (ref + (b["x"], b["y"], b["number"], b["depth"]) + out + (q(f),))
            return (self.branch(call, out) if out[0] else [call]), False
        if t == "DB":
            ref = target(b["skill"])
            cond = "me.basicCondition(%d, %s, %s)" % (b["condition"],
                    "true^" if b["inverted"] else "false^", "true^" if b["disabled"] else "false^")
            return (self.branch(cond, ref) if ref else ["# DB to nothing"]), False
        if t == "C":
            when = "hits" if b["hits"] else "uncond" if b["uncond"] else "fails"
            n = b["skill"]["number"] if b["skillCancelCondition"] else -1
            return ["me.cancel(%s, %d, %d, %d)" % (q(when), b["from"], b["to"], n)], False
        if t == "R":
            keys = ["hitsStand", "hitsCrouched", "hitsAir", "guardStand", "guardCrouched", "guardAir"]
            return ["me.reactions(%s)" % ", ".join(str(b[k]["number"]) for k in keys)], False
        if t == "PS":
            return ["me.pause(%d, %d)" % (b["playerTime"], b["enemyTime"])], False
        if t == "GP":
            return ["me.gauges(%d, %d, %d, %d)" % (b["playerLifeGauge"], b["playerSpecialGauge"],
                                                   b["enemyLifeGauge"], b["enemySpecialGauge"])], False
        if t == "EB":
            c = b["rgba"]
            x, y = b["shakeBgX"], b["shakeBgY"]
            return ["me.screen(%d, %d, %d, %d, %d, %d, %s, %d, %d, %d, %d, %d, %d)" % (
                b["fadingType"], c["r"], c["g"], c["b"], c["a"], b["duration"],
                q(flags(b, ["player", "enemy", "bg", "system"])),
                x["type"], x["shake"], x["duration"], y["type"], y["shake"], y["duration"])], False
        if t == "AI":
            c = b["rgba"]
            return ["me.afterimage(%d, %d, %d, %d, %d, %d, %d, %d)" % (b["num"], b["time"], b["option"], b["fadingType"],
                                                                       c["r"], c["g"], c["b"], c["a"])], False
        if t == "COLOR":
            c = b["rgba"]
            return ["me.color(%d, %d, %d, %d, %d)" % (b["option"], c["r"], c["g"], c["b"], c["a"])], False
        if t == "RC":
            return ["me.commonImage(%d, %d, %d, %s)" % (b["commonImage"]["number"], b["x"], b["y"],
                                                        q(flags(b, ["in", "turnX", "turnY", "same"])))], False
        if t == "RP":
            return ["me.hitJunction(%d, %d, %d, %s)" % (b["hitJunction"]["number"], b["x"], b["y"],
                                                        q(flags(b, ["in", "turnX"])))], False
        return ["# %s block (not decoded)" % t], False

    # -- whole skill -------------------------------------------------------
    def segments(self):
        """[(label, [lines], ends_flow)] — dead blocks after an end are dropped."""
        segs = []
        label_set = set(self.labels)
        cur, dead = None, False
        for i, b in enumerate(self.blocks):
            if i in label_set:
                cur = [i, [], False]
                segs.append(cur)
                dead = False
            if dead:
                continue
            self.here = i
            lines, ends = self.block(i, b)
            if self.dispatch and b["type"] in CONDITIONAL and any(x.startswith("pc := ") for x in lines):
                ends = True
            cur[1].extend(lines)
            if ends:
                dead = True
                cur[2] = True
        return segs

    def emit(self):
        head = "public^let^s%04d = p^me:Fighter, at:number^{    # %s" % (self.n, self.skill["name"])
        body = []
        segs = self.segments()
        guard = ["if^me.spin() { yield^ }"]
        if not segs:
            body.append("_yield^")
        elif not self.dispatch:
            lines, ends = segs[0][1], segs[0][2]
            suspends = any("await^" in x or "yield^" in x for x in lines)
            if self.loops:
                body.append("repeat^while^me.alive {")
                inner = ([] if suspends else guard) + lines + ([] if ends else ["return^"])
                body += ["    " + s for s in inner]
                body.append("}")
            else:
                body += lines
                if not suspends:
                    body.insert(0, "_yield^")
        else:
            body.append("var^pc = at")
            body.append("repeat^while^me.alive {")
            body.append("    " + guard[0])
            for k, (label, lines, ends) in enumerate(segs):
                body.append("    if^pc = %d {" % label)
                body += ["        " + s for s in lines]
                if not ends:
                    if k + 1 < len(segs):
                        body.append("        pc := %d" % segs[k + 1][0])
                    else:
                        body.append("        return^")
                body.append("    }")
            body.append("    if^pc < 0 { return^ }")
            body.append("}")
        return [head] + ["    " + s for s in body] + ["}"]


def fighter_from(folder):
    """src/fighter.lh as a require^ path relative to `folder`."""
    import os
    return os.path.relpath(Path("src/fighter.lh"), folder).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", type=Path)
    ap.add_argument("id", help="ASCII id for module paths, e.g. yui")
    ap.add_argument("--out", type=Path, default=None, help="default src/chara, or src/stages with --stage")
    ap.add_argument("--stage", action="store_true", help="the file is a stage: its scripts are layers")
    ap.add_argument("--layers", action="store_true",
                    help="E hides the script's image (stages always; the system file's HUD scripts)")
    args = ap.parse_args()

    d = json.loads(args.json.read_text(encoding="utf-8-sig"))
    skills = d["skills"]
    SkillWriter.stage = args.stage or args.layers
    entries = {}
    for s in skills:
        for blk in s["blocks"]:
            for n, b in jump_refs(blk):
                entries.setdefault(n, set()).add(b)

    out = args.out or Path("src/stages" if args.stage else "src/chara")
    kind = "stages" if args.stage else "skills"
    root = out / args.id
    (root / "skills").mkdir(parents=True, exist_ok=True)
    for old in (root / "skills").glob("s*.lh"):
        old.unlink()
    header = ["# Generated from %s by tools/fm2k_convert/gen_skills.py — a draft to edit." % args.json.name]

    chunks = []
    for first in range(0, len(skills), PER_FILE):
        mod = "s%04d" % first
        lines = header + ["module^vp.%s.%s.%s" % (kind, args.id, mod), "",
                          'require^"%s"' % fighter_from(root / "skills"), ""]
        lines.append("let^Fighter = vp.fighter.Fighter")
        for n in range(first, min(first + PER_FILE, len(skills))):
            lines.append("")
            lines += SkillWriter(n, skills[n], entries).emit()
        (root / "skills" / (mod + ".lh")).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        chunks.append((mod, first, min(first + PER_FILE, len(skills))))

    index = header + ["module^vp.%s.%s.index" % (kind, args.id), "", 'require^"%s"' % fighter_from(root)]
    index += ['require^"skills/%s.lh"' % mod for mod, _, _ in chunks]
    index += ["", "# Skills by number, the character's command table (in priority order) and",
              "# each skill's level (what C blocks cancel against).",
              "public^let^install = p^me:vp.fighter.Fighter{"]
    for mod, a, b in chunks:
        for n in range(a, b):
            index.append("    me.skills[%d] := vp.%s.%s.%s.s%04d" % (n, kind, args.id, mod, n))
    for n, sk in enumerate(skills):
        lv = sk["blocks"][0].get("level", 0) if sk["blocks"] and sk["blocks"][0]["type"] == "Settings" else 0
        if lv:
            index.append("    me.levels[%d] := %d" % (n, lv))
    # Reaction number (the attacker's R block) -> this character's hit skill and spark.
    for i, r in enumerate(d.get("hitJunctionsSkills", [])):
        hit, spark = r["hitJunction"]["number"], r["spark"]["number"]
        if hit or spark:
            index.append("    me.reactsWith(%d, %d, %d)" % (i, hit, spark))
    if "settings" in d:
        st = d["settings"]
        index.append("    me.lifeMax := %d" % st["lifeGaugeMax"])
        index.append("    me.life := %d" % st["lifeGaugeMax"])
        index.append("    me.guardDamageRate := %d" % st.get("hRatio", 0))
        index.append("    me.closeRange := %d" % st.get("interval", 0))
        index.append("    me.specialPer := %d" % st["specialGaugeMax"])
        index.append("    me.stockMax := %d" % st["specialMaxStock"])
        index.append("    me.special := %d" % (st["specialGaugeMax"] * min(st["startStock"], st["specialMaxStock"])))
    for c in d.get("commands", []):
        dirs, buttons = steps_of(c["steps"])
        refs = [c[k]["number"] for k in ("airSkill", "standSkill", "standFarSkill", "crouchedSkill")]
        if not any(refs) or buttons == "{  }" and all(x == 0 for x in eval(dirs.replace("{", "[").replace("}", "]"))):
            continue
        index.append("    me.addCommand(%s, %d, %d, %d, %d, %d, %s, %s, {}, {})"
                     % ((q(c["name"]), c["time"]) + tuple(refs) + (dirs, buttons)))
    index.append("}")
    if args.stage:
        # Layers are the named scripts after "none", drawn in order; the players
        # go where the script named プレーヤー位置 stands.
        layers = [n for n in range(1, len(skills)) if skills[n]["name"] and skills[n]["blocks"]]
        players = next((n for n in layers if skills[n]["name"] == "プレーヤー位置"), -1)
        index += ["", "# Script numbers of the layers, back to front, and where the players go.",
                  "public^let^layers : t^{number^[]} = { %s }" % ", ".join(map(str, layers)),
                  "public^let^players = %d" % players]
    (root / "skills.lh").write_text("\n".join(index) + "\n", encoding="utf-8", newline="\n")
    print("%d skills -> %s (%d files)" % (len(skills), root, len(chunks)))


if __name__ == "__main__":
    main()
