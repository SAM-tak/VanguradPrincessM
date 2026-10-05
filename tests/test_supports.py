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



if __name__ == "__main__":
    unittest.main()
