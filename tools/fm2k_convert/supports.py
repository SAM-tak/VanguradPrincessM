"""Identify the five support actions in generated script.lton files.

This is a read-only extraction/audit step, not a replacement for the runtime.
Skill numbers are resolved by names in each character, never by fixed ranges.
Usage: python supports.py assets --out build/support-actions.json
"""

import argparse
import json
import re
from pathlib import Path


# Public inputs, request values (character variable 76), FM2K direction masks.
# FM2K direction numbers are not numpad notation. Zero is the default branch.
ACTIONS = {"5D": (101, 0), "2D": (150, 4), "3D": (130, 3),
           "6D": (110, 2), "4D": (102, 10)}
SUPPORTS = {
    "えこ": (101, "攻撃分岐", "さぽーとふぇいす2ｐ"),
    "シエラ": (102, "攻撃ヴんき", "しえらコマンド"),
    "ジュリエット": (103, "パートナー分岐", "ぱーとなーふぇいす"),
    "かなえ": (104, "ヨメ攻撃分岐", "ヨメふぇいす"),
    "ヒルダ": (105, "オマケ分岐", "おまけふぇいす"),
}


def read_skills(path, libraries=None):
    """Read the deliberately small format emitted by gen_script.skill_lines."""
    if libraries is None:
        libraries = {}
    parts = re.split(r'(?m)^\{ name = ', path.read_text(encoding="utf-8"))[1:]
    skills = []
    for part in parts:
        head = re.match(r'("(?:[^"\\]|\\.)*"), level = (-?\d+), blocks = \{', part)
        if not head:
            raise ValueError(f"{path}: unsupported skill header")
        blocks = []
        for line in part.splitlines()[1:]:
            line = line.strip()
            if line.startswith('{ "'):
                if not line.endswith(" },"):
                    raise ValueError(f"{path}: unsupported block: {line}")
                blocks.append(json.loads("[" + line[1:-2] + "]"))
        reference = re.search(r'support = ("(?:[^"\\]|\\.)*"), base = (\d+), recipe = \{([^}]*)\}', part)
        if reference:
            library = json.loads(reference[1])
            if library not in SUPPORTS and library != "common":
                raise ValueError(f"{path}: unknown support {library!r}")
            source = path.parents[2] / "supports" / library / "script.lton"
            if source not in libraries:
                libraries[source] = read_skills(source, libraries)
            base = libraries[source][int(reference[2])]
            recipe = json.loads("[" + reference[3] + "]")
            blocks = expand_recipe(base["blocks"], recipe, blocks)
        skills.append({"name": json.loads(head[1]), "level": int(head[2]), "blocks": blocks})
    if not skills:
        raise ValueError(f"{path}: no skills found")
    return skills


def expand_recipe(base, recipe, changes):
    if len(recipe) % 2:
        raise ValueError("odd support recipe length")
    out, used = [], 0
    for start, count in zip(recipe[::2], recipe[1::2]):
        if count <= 0 or start < -1:
            raise ValueError("invalid support recipe range")
        source, offset = (changes, used) if start == -1 else (base, start)
        if offset + count > len(source):
            raise ValueError("support recipe out of bounds")
        out.extend(source[offset:offset + count])
        if start == -1:
            used += count
    if used != len(changes):
        raise ValueError("unused support changes")
    return out


def named(skills, name):
    matches = [i for i, sk in enumerate(skills) if sk["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"expected one {name!r}, found {matches}")
    return matches[0]


def request_targets(blocks, request):
    """Only active equality branches count; unused FM2K operands retain garbage."""
    return sorted({(b[7], b[8]) for b in blocks
                   if b[0] == "V" and b[1] == 76 and b[2] == 0
                   and b[5] == 1 and b[6] == request and b[7] >= 0})


def describe_target(skills, target):
    skill, block = target
    if not 0 <= skill < len(skills) or not 0 <= block < len(skills[skill]["blocks"]):
        raise ValueError(f"invalid support entry {skill}:{block}")
    return {"skill": skill, "name": skills[skill]["name"], "block": block}


def command_request(skills, skill, block):
    """Follow the request-setting fallthrough of a HUD COM branch.

    Gauge/cooldown checks can reject an input. This identifies its request when
    those checks pass, not whether the action can currently be used.
    """
    seen = set()
    while (skill, block) not in seen:
        seen.add((skill, block))
        bs = skills[skill]["blocks"]
        if not 0 <= block < len(bs):
            break
        b = bs[block]
        if b[0] == "V" and b[1] == 76 and b[2] == 1 and b[3] == 0:
            return b[4]
        if b[0] == "SG":
            skill, block = b[1:3]
            if skill < 0:
                break
            continue
        if b[0] in ("E", "COM", "Rnd", "SC", "SF"):
            break
        block += 1
    raise ValueError(f"cannot resolve command request at {skill}:{block}")


def identify(skills):
    result = {}
    for name, (selection, dispatch_name, hud_name) in SUPPORTS.items():
        dispatch = named(skills, dispatch_name)
        hud = named(skills, hud_name)
        commands = {}
        for i, b in enumerate(skills[hud]["blocks"]):
            if b[0] == "COM" and b[4] == 1 and b[6] == 8 and b[2] >= 0:
                if b[5] in commands:
                    raise ValueError(f"{name}: duplicate D input direction {b[5]}")
                commands[b[5]] = (i, b)
        if not {direction for _, direction in ACTIONS.values()} <= set(commands):
            raise ValueError(f"{name}: missing D commands {list(commands)}")
        actions = {}
        for action, (request, direction) in ACTIONS.items():
            targets = request_targets(skills[dispatch]["blocks"], request)
            if len(targets) != 1:
                raise ValueError(f"{name} {action}: ambiguous entries {targets}")
            command_block, command = commands[direction]
            actual = command_request(skills, command[2], command[3])
            actions[action] = {"request": request, "entry": describe_target(skills, targets[0]),
                               "actual_request": actual,
                               "command": {"skill": hud, "block": command_block}}
        # Kurumi's collaboration request. This is a separate owner hook, not D input.
        extras = [describe_target(skills, t) for t in request_targets(skills[dispatch]["blocks"], 93)]
        aliases = [{"direction_code": direction,
                    "request": command_request(skills, b[2], b[3]),
                    "command": {"skill": hud, "block": i}}
                   for direction, (i, b) in commands.items()
                   if direction not in {d for _, d in ACTIONS.values()}]
        result[name] = {"selection": selection, "dispatch": dispatch,
                        "actions": actions, "additional_inputs": aliases,
                        "owner_request_93": extras}
    return result


def audit(root):
    characters = {}
    libraries = {}
    for path in sorted((root / "characters").glob("*/script.lton")):
        skills = read_skills(path, libraries)
        # The dummy character has no support dispatcher. Do not infer by folder name.
        if not any(sk["name"] == "攻撃分岐" for sk in skills):
            continue
        characters[path.parent.name] = identify(skills)
    if not characters:
        raise ValueError("no support-bearing character scripts found")
    reference = characters["ゆい"]
    differences = []
    for character, supports in characters.items():
        for support, data in supports.items():
            for action, entry in data["actions"].items():
                if entry["entry"]["name"] != reference[support]["actions"][action]["entry"]["name"]:
                    differences.append({"character": character, "support": support, "action": action,
                                        "entry": entry["entry"],
                                        "reference_entry": reference[support]["actions"][action]["entry"]})
    return {"schema": 1, "request_variable": 76, "characters": characters,
            "entry_differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.assets)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mismatches = sum(action["request"] != action["actual_request"]
                     for supports in report["characters"].values()
                     for support in supports.values() for action in support["actions"].values())
    print(f"{len(report['characters'])} characters: five action entries found for all five supports; "
          f"{mismatches} input differences -> {args.out}")


if __name__ == "__main__":
    main()
