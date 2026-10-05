"""Legacy Yui normalization helpers, retained for reading old conversion records.

The command now delegates to owner_supports.py and preserves owner differences.
The old normalization functions below are historical utilities, not the active
export path. Run gen_script.py from original JSON before the first migration.
"""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
import json
from pathlib import Path
from layout import metadata_path, media_path
import re

from gen_script import lton_list, lton_str
from supports import SUPPORTS, expand_recipe, identify, named, read_skills, source_script


# Named boundaries in the reference layout. Other characters are matched by
# skill name, not by numerical intervals (Kurumi inserts and removes skills).
STARTS = {"えこ": "オプション00", "シエラ": "サポートはじめ",
          "ジュリエット": "パートナーはじめ", "かなえ": "よめはじめ",
          "ヒルダ": "オマケスタート"}
ALIASES = {("ルナ", "発射"): "らしいん"}
ABSENT = {("くるみ", "サポか")}
TARGETS = {"SG": 1, "SC": 1, "SF": 1, "V": 7, "Rnd": 3, "COM": 2,
           "GL": 3, "GS": 4, "DS": 1, "O": 1, "C": 3}


def target_index(block):
    if block[0] == "V" and block[5] == 0:
        return None
    i = TARGETS.get(block[0])
    return i if i and block[i] > 0 else None


def signature(block):
    """Compare instructions independently of asset/branch numbering."""
    b = block[:]
    i = target_index(b)
    if i:
        b[i] = 0
        if b[0] != "C":
            b[i + 1] = 0
    if b[0] in ("I", "S"):
        b[1] = 0
    if b[0] == "V":
        if b[2] == 0:
            b[3] = b[4] = 0
        if b[5] == 0:
            b[6] = b[7] = b[8] = 0
    return tuple(b)


def block_map(before, after):
    """Relocate retained instructions; removed instructions continue at the next survivor."""
    out = {0: 0, len(before): len(after)}
    matcher = SequenceMatcher(None, list(map(signature, before)), list(map(signature, after)), autojunk=False)
    for match in matcher.get_matching_blocks():
        for offset in range(match.size):
            out[match.a + offset] = match.b + offset
    next_block = len(after)
    for i in range(len(before) - 1, -1, -1):
        if i in out:
            next_block = out[i]
        else:
            out[i] = next_block
    out[0] = 0
    return out


def normalize(reference, original, local_map, character):
    """Link canonical branches to the owner's helpers; preserve only request-93 hooks."""
    core = set(local_map)
    votes = defaultdict(Counter)
    needed = set()
    for canonical, local in local_map.items():
        a, b = reference[canonical]["blocks"], original[local]["blocks"]
        for block in a:
            k = target_index(block)
            if k and block[k] not in core:
                needed.add(block[k])
        matches = SequenceMatcher(None, list(map(signature, a)), list(map(signature, b)), autojunk=False)
        for match in matches.get_matching_blocks():
            for offset in range(match.size):
                x, y = a[match.a + offset], b[match.b + offset]
                k, j = target_index(x), target_index(y)
                if k and j and x[k] not in core:
                    votes[x[k]][y[j]] += 1
    mapping = dict(local_map)
    for n in sorted(needed):
        if votes[n]:
            mapping[n] = votes[n].most_common(1)[0][0]
        else:
            # Some boss-only copies omit a call entirely. Match the helper's
            # structure, not auto-generated names such as "Skill 5".
            a = list(map(signature, reference[n]["blocks"]))
            scores = sorted((SequenceMatcher(None, a, list(map(signature, sk["blocks"])), autojunk=False).ratio(), i)
                            for i, sk in enumerate(original) if i not in local_map.values())
            if scores[-1][0] < .8 or scores[-1][0] == scores[-2][0]:
                raise ValueError(f"{character}: ambiguous external helper {n}: {scores[-2:]}")
            mapping[n] = scores[-1][1]
    # Kurumi's four HUD adapters also contain request-93 waiting/return paths.
    # Keep these small adapters; the attack implementations below remain common.
    adapters = {named(reference, SUPPORTS[n][2]) for n in list(SUPPORTS)[:4]} if character == "くるみ" else set()
    hooks = {}
    if character == "くるみ":
        for n in list(SUPPORTS)[:4]:
            c = named(reference, SUPPORTS[n][1])
            branches = [b for b in original[local_map[c]]["blocks"]
                        if b[0] == "V" and b[1] == 76 and b[5] == 1 and b[6] == 93]
            if not branches:
                raise ValueError(f"Kurumi/{n}: missing collaboration hook")
            hooks[c] = branches[0][:]
    to_owner = {n: block_map(reference[n]["blocks"], original[mapping[n]]["blocks"])
                for n in needed | adapters}
    to_common = {local: block_map(original[local]["blocks"], reference[n]["blocks"])
                 for n, local in local_map.items() if n not in adapters}
    reverse = {local: n for n, local in local_map.items()}

    def incoming(block):
        k = target_index(block)
        if k and block[0] != "C" and block[k] in to_common:
            n = reverse[block[k]]
            at = to_common[block[k]].get(block[k + 1])
            if at is None:
                raise ValueError(f"{character}: invalid incoming support target {block}")
            block[k + 1] = at + (1 if n in hooks and at >= 1 else 0)

    result = deepcopy(original)
    for i, sk in enumerate(result):
        if i not in local_map.values() or reverse[i] in adapters:
            for block in sk["blocks"]:
                incoming(block)
    for n, local in local_map.items():
        if n in adapters:
            continue
        blocks = deepcopy(reference[n]["blocks"])
        for block in blocks:
            k = target_index(block)
            if k:
                target = block[k]
                block[k] = mapping[target]
                if block[0] != "C":
                    at = block[k + 1]
                    if target in to_owner:
                        at = to_owner[target].get(at)
                        if at is None:
                            raise ValueError(f"{character}: invalid external target {block}")
                    elif target in hooks and at >= 1:
                        at += 1
                    block[k + 1] = at
        if n in hooks:
            blocks.insert(1, hooks[n])
        result[local] = {"name": original[local]["name"], "level": reference[n]["level"], "blocks": blocks}
    return result


def recipe_for(base, blocks):
    recipe, changes = [], []
    matcher = SequenceMatcher(None, [tuple(b) for b in base], [tuple(b) for b in blocks], autojunk=False)
    for op, a, z, b, y in matcher.get_opcodes():
        if op == "equal":
            recipe.extend((a, z - a))
        elif b < y:
            recipe.extend((-1, y - b))
            changes.extend(blocks[b:y])
    if expand_recipe(base, recipe, changes) != blocks:
        raise ValueError("support recipe did not reconstruct original blocks")
    return recipe, changes


def skill_text(skill):
    lines = ["{ name = %s, level = %d, blocks = {" % (lton_str(skill["name"]), skill["level"])]
    lines.extend("    %s," % lton_list(b) for b in skill["blocks"])
    return "\n".join(lines + ["} },\n"])


def reference_text(skill, support, base, recipe, changes):
    lines = ["{ name = %s, level = %d, blocks = {}, support = %s, base = %d, recipe = %s, changes = {"
             % (lton_str(skill["name"]), skill["level"], lton_str(support), base, lton_list(recipe))]
    lines.extend("    %s," % lton_list(b) for b in changes)
    return "\n".join(lines + ["} },\n"])


def plan(root):
    root = metadata_path(root)
    scripts, texts = {}, {}
    fixed_outputs = {}
    loaded = {}
    for path in sorted((root / "characters").glob("*/script.lton")):
        # Boss Hilda's names resemble the selectable supports, but their bodies,
        # attacks and fixed dispatcher belong to the boss. Never normalize them.
        if path.parent.name == "ヒルダ":
            from support_namespaces import emit
            from layout import conversion_path
            text = source_script(path).read_text(encoding="utf-8")
            skills = read_skills(path, loaded)
            header = re.split(r'(?m)^\{ name = ', text, maxsplit=1)[0]
            fixed_outputs[conversion_path(path.with_name('support-source.lton'))] = text
            fixed_outputs[path] = header + 'fixedSupport = true^,\n' + ''.join(emit(sk, i) for i, sk in enumerate(skills))
            continue
        skills = read_skills(path, loaded)
        if any(sk["name"] == "攻撃分岐" for sk in skills):
            identify(skills)
            scripts[path.parent.name] = skills
            texts[path.parent.name] = source_script(path).read_text(encoding="utf-8")
    reference = deepcopy(scripts["ゆい"])
    support_names = list(SUPPORTS)
    boundaries = [named(reference, STARTS[n]) for n in support_names] + [named(reference, "kage2  ")]
    if boundaries != sorted(set(boundaries)):
        raise ValueError("support reference layout changed")
    groups = {}
    for index, support in enumerate(support_names):
        groups[support] = list(range(boundaries[index], boundaries[index + 1])) + [named(reference, SUPPORTS[support][2])]
    # The gauge recovery routine is tucked behind an unrelated player guard
    # skill. Extract its tail so boss copies lacking it get the same behavior.
    recovery_name = "共通サポートゲージ回復"
    existing = next((i for i, sk in enumerate(reference) if sk["name"] == recovery_name), None)
    recovery = existing if existing is not None else len(reference)
    if existing is None:
        blocks = deepcopy(reference[766]["blocks"][3:])
        for block in blocks:
            k = target_index(block)
            if k and block[k] == 766:
                block[k], block[k + 1] = recovery, block[k + 1] - 3
        reference.append({"name": recovery_name, "level": 10, "blocks": blocks})
        for indices in groups.values():
            for n in indices:
                for block in reference[n]["blocks"]:
                    k = target_index(block)
                    if k and block[k] == 766 and block[k + 1] >= 3:
                        block[k], block[k + 1] = recovery, block[k + 1] - 3
    groups["common"] = [recovery]
    guard_name = "共通サポートガード表示"
    guard = next((i for i, sk in enumerate(reference) if sk["name"] == guard_name), None)
    if guard is None:
        guard = len(reference)
        reference.append({**deepcopy(reference[771]), "name": guard_name})
        for n in [i for indices in groups.values() for i in indices] + [guard]:
            for block in reference[n]["blocks"]:
                k = target_index(block)
                if k and block[k] == 771:
                    block[k] = guard
    groups["common"].append(guard)
    # Support code must never call an owner's unrelated helper just because
    # its number/name matches Yui's. Copy the complete dependency closure into
    # support media space, preserving the owner's original helpers untouched.
    # Reuse generated names on subsequent runs so the transformation is stable.
    core = {n for indices in groups.values() for n in indices}
    helper_prefix = "共通サポート補助_"
    generated = {i for i, sk in enumerate(reference) if sk["name"].startswith(helper_prefix)}
    core.update(generated)
    groups["common"].extend(sorted(generated))
    seen, todo = set(core), list(core)
    while todo:
        n = todo.pop()
        for block in reference[n]["blocks"]:
            k = target_index(block)
            if k and block[k] not in seen:
                seen.add(block[k])
                todo.append(block[k])
    helpers = {}
    for n in sorted(seen - core):
        clone = len(reference)
        helpers[n] = clone
        reference.append({**deepcopy(reference[n]), "name": f"{helper_prefix}{n}_{reference[n]['name']}"})
        groups["common"].append(clone)
    for indices in groups.values():
        for n in indices:
            for block in reference[n]["blocks"]:
                k = target_index(block)
                if k and block[k] in helpers:
                    block[k] = helpers[block[k]]
    mappings, normalized = {}, {}
    for character, original in scripts.items():
        original = deepcopy(original)
        mapping = {}
        for indices in groups.values():
            for n in indices:
                name = ALIASES.get((character, reference[n]["name"]), reference[n]["name"])
                if not any(sk["name"] == name for sk in original) and ((character, name) in ABSENT or name in (recovery_name, guard_name) or name.startswith(helper_prefix)):
                    original.append(deepcopy(reference[n]))
                mapping[n] = named(original, name)
        mappings[character] = mapping
        normalized[character] = normalize(reference, original, mapping, character)
    outputs, replacements = {}, {c: {} for c in scripts}
    stats = {"characters": len(scripts), "bindings": 0, "bound_blocks": 0,
             "library_blocks": 0, "changed_blocks": 0, "reused_blocks": 0}
    for support in groups:
        canonical = [reference[n] for n in groups[support]]
        library = []
        for slot, model in enumerate(canonical):
            variants = {}
            for character, skills in normalized.items():
                local = mappings[character][groups[support][slot]]
                variants[character] = (local, skills[local])
            common = model
            library.append(common)
            stats["library_blocks"] += len(common["blocks"])
            for character, (local, skill) in variants.items():
                if local in replacements[character]:
                    raise ValueError(f"duplicate support binding: {character}/{local}")
                recipe, changes = recipe_for(common["blocks"], skill["blocks"])
                replacements[character][local] = reference_text(skill, support, slot, recipe, changes)
                stats["bindings"] += 1
                stats["bound_blocks"] += len(skill["blocks"])
                stats["changed_blocks"] += len(changes)
                stats["reused_blocks"] += len(skill["blocks"]) - len(changes)
        header = '# Canonical Yui support definitions; generated by share_supports.py.\nsupportMedia = "assets/supports/common",\nlayers = false^,\n'
        outputs[root / "supports" / support / "script.lton"] = header + "".join(map(skill_text, library))
    for character, text in texts.items():
        parts = re.split(r'(?m)(?=^\{ name = )', text)
        if len(parts) != len(scripts[character]) + 1:
            raise ValueError(f"{character}: unexpected script format")
        outputs[root / "characters" / character / "script.lton"] = parts[0] + "".join(
            replacements[character].get(i, skill_text(sk)) for i, sk in enumerate(normalized[character]))
    # Media belongs to the support definitions, not to the owner or its palette.
    for kind, op in (("images", "I"), ("sounds", "S")):
        used = {b[1] for indices in groups.values() for n in indices
                for b in reference[n]["blocks"] if b[0] == op}
        lines = [line for line in (root / "characters" / "ゆい" / f"{kind}.lton").read_text(encoding="utf-8").splitlines()
                 if line and not line.startswith("#")]
        lines = [re.sub(r'file = "([^"]+)"', r'asset = "assets/characters/ゆい/\1"', line) if i in used else "nil^,"
                 for i, line in enumerate(lines)]
        outputs[root / "supports" / "common" / f"{kind}.lton"] = "# Yui support media; generated by share_supports.py.\n" + "\n".join(lines) + "\n"
    from support_namespaces import compile_namespaces
    stats["namespaces"] = compile_namespaces(root, reference, groups, normalized, mappings, outputs)
    outputs.update(fixed_outputs)
    stats["original_bytes"] = sum(len(t.encode("utf-8")) for t in texts.values())
    stats["original_bytes"] += sum(p.stat().st_size for p in outputs if p.exists() and "supports" in p.relative_to(root).parts)
    stats["factored_bytes"] = sum(len(t.encode("utf-8")) for t in outputs.values())
    stats["runtime_bytes"] = sum(len(t.encode("utf-8")) for p, t in outputs.items()
                                 if p.name != 'support-source.lton')
    return outputs, stats


def main():
    # Keep the old command safe: never silently restore Yui-only balance.
    from owner_supports import main as extract_owners
    extract_owners()


if __name__ == "__main__":
    main()
