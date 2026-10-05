import sys
import unittest
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "fm2k_convert"))
import supports
import share_supports


def fixture():
    # Deliberately unrelated skill numbers: extraction must resolve names.
    skills = [{"name": "unrelated", "blocks": [["E"]]}]
    for _, (_, dispatcher, hud) in supports.SUPPORTS.items():
        dispatch = len(skills)
        skills.extend([{"name": dispatcher, "blocks": []}, {"name": hud, "blocks": []}])
        for action, (request, direction) in supports.ACTIONS.items():
            target = len(skills)
            skills.append({"name": action, "blocks": [["E"]]})
            skills[dispatch]["blocks"].append(["V", 76, 0, 0, 0, 1, request, target, 0])
            bs = skills[dispatch + 1]["blocks"]
            bs.extend([["COM", 20, dispatch + 1, len(bs) + 1, 1, direction, 8],
                       ["V", 76, 1, 0, request, 0, 0, -1, 0], ["E"]])
    return skills


class SupportActionsTest(unittest.TestCase):
    def test_support_helpers_do_not_escape_to_owner_skills(self):
        root = Path(__file__).resolve().parents[1] / "data"
        allowed_huds = {v[2] for v in list(supports.SUPPORTS.values())[:4]}
        for path in (root / "characters").glob("*/script.lton"):
            if path.parent.name == "だみー":
                continue
            skills = supports.read_skills(path)
            parts = re.split(r'(?m)^\{ name = ', supports.source_script(path).read_text(encoding="utf-8"))[1:]
            bound = {i for i, part in enumerate(parts) if "support = " in part}
            for i in bound:
                for block in skills[i]["blocks"]:
                    k = share_supports.target_index(block)
                    if not k or block[k] in bound:
                        continue
                    collaboration = (skills[i]["name"] in allowed_huds or
                                     block[0] == "V" and block[1] == 76 and block[5:7] == [1, 93])
                    self.assertTrue(path.parent.name == "くるみ" and collaboration,
                                    (path.parent.name, skills[i]["name"], block))

    def test_eri_support_movement_does_not_play_owner_voice(self):
        root = Path(__file__).resolve().parents[1] / "data"
        skills = supports.read_skills(root / "characters/えり/script.lton")
        helper = supports.named(skills, "共通サポート補助_353_ダッシュエフェクト")
        self.assertEqual(skills[helper]["blocks"], [["Settings", 10, 0]])
        for name in ["サポート移動前", "サポート移動後ろｒ", "りふれくたー", "おまけ移動前", "おまけ移動前2ｐ"]:
            blocks = skills[supports.named(skills, name)]["blocks"]
            self.assertTrue(any(b[0] == "O" and b[1:3] == [helper, 0] for b in blocks), name)
            self.assertFalse(any(b[0] == "O" and b[1] == 353 for b in blocks), name)
        self.assertEqual(skills[353]["blocks"][1], ["S", 29])  # Owner voice remains available.

    def test_recipe_insert_delete_and_reordered_blocks(self):
        base = [["I", 1], ["V", 2], ["I", 3], ["E"]]
        target = [["V", 2], ["I", 4], ["I", 1], ["E"]]
        recipe, changes = share_supports.recipe_for(base, target)
        self.assertEqual(supports.expand_recipe(base, recipe, changes), target)
        with self.assertRaises(ValueError):
            supports.expand_recipe(base, [0, 20], [])
        with self.assertRaises(ValueError):
            supports.expand_recipe(base, [0], [])

    def test_removed_block_entry_relocates_to_next_instruction(self):
        before = [["Settings", 10, 0], ["V", 71, 2, 0, 1, 0, 0, -1, 0], ["I", 1, 2, 0, 0, ""], ["E"]]
        after = [before[0], before[2], before[3]]
        mapping = share_supports.block_map(before, after)
        self.assertEqual(mapping, {0: 0, 1: 1, 2: 1, 3: 2, 4: 3})

    def test_resolves_all_five_actions_without_fixed_skill_numbers(self):
        result = supports.identify(fixture())
        self.assertEqual(len(result), 5)
        for support in result.values():
            self.assertEqual(set(support["actions"]), set(supports.ACTIONS))
            for action, data in support["actions"].items():
                self.assertEqual(data["entry"]["name"], action)
                self.assertEqual(data["request"], data["actual_request"])

    def test_inactive_and_write_operands_are_not_dispatch_branches(self):
        blocks = [["V", 76, 0, 0, 0, 0, 101, 900, 0],
                  ["V", 76, 1, 0, 101, 1, 101, 901, 0],
                  ["V", 76, 0, 0, 0, 1, 101, 902, 0]]
        self.assertEqual(supports.request_targets(blocks, 101), [(902, 0)])

    def test_alias_and_owner_hook_do_not_become_sixth_regular_action(self):
        skills = fixture()
        dispatch = supports.named(skills, "攻撃分岐")
        hud = supports.named(skills, "さぽーとふぇいす2ｐ")
        skills[dispatch]["blocks"].append(["V", 76, 0, 0, 0, 1, 93, 0, 0])
        bs = skills[hud]["blocks"]
        bs.extend([["COM", 20, hud, len(bs) + 1, 1, 9, 8],
                   ["V", 76, 1, 0, 110, 0, 0, -1, 0], ["E"]])
        eko = supports.identify(skills)["えこ"]
        self.assertEqual(len(eko["actions"]), 5)
        self.assertEqual(eko["owner_request_93"][0]["skill"], 0)
        self.assertEqual(eko["additional_inputs"][0]["request"], 110)

    def test_converted_regular_definitions_match_yui(self):
        root = Path(__file__).resolve().parents[1] / "data"
        if not (root / "supports" / "えこ" / "script.lton").exists():
            self.skipTest("converted assets unavailable")
        cache = {}
        yui = supports.read_skills(root / "characters" / "ゆい" / "script.lton", cache)
        starts = [supports.named(yui, n) for n in share_supports.STARTS.values()]
        indices = list(range(starts[0], supports.named(yui, "kage2  ")))
        indices += [supports.named(yui, v[2]) for v in supports.SUPPORTS.values()]

        def body(blocks):
            result = []
            for raw in blocks:
                b = raw[:]
                if b[0] == "V" and b[1] == 76 and b[5] == 1 and b[6] == 93:
                    continue
                k = share_supports.target_index(b)
                if k:
                    b[k] = 0
                    if b[0] != "C":
                        b[k + 1] = 0
                result.append(b)
            return result

        for path in sorted((root / "characters").glob("*/script.lton")):
            if path.parent.name == "だみー":
                continue
            skills = supports.read_skills(path, cache)
            report = supports.identify(skills)
            for support in report.values():
                for action in support["actions"].values():
                    self.assertEqual(action["request"], action["actual_request"])
            for n in indices:
                name = yui[n]["name"]
                if path.parent.name == "くるみ" and name in [v[2] for v in list(supports.SUPPORTS.values())[:4]]:
                    continue  # Explicit collaboration HUD adapters.
                local = supports.named(skills, share_supports.ALIASES.get((path.parent.name, name), name))
                self.assertEqual(body(skills[local]["blocks"]), body(yui[n]["blocks"]), (path.parent.name, name))


if __name__ == "__main__":
    unittest.main()
