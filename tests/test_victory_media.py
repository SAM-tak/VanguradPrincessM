import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/fm2k_convert'))
from victory_media import collect
from supports import read_skills


class VictoryMediaTests(unittest.TestCase):
    def test_winner_prunes_opponent_and_random_keep_both(self):
        skills = [{'name': '', 'blocks': []}, {'name': 'layer', 'blocks': [
            ['V', 129, 0, 0, 0, 1, 100, 1, 3],
            ['I', 99], ['E'],
            ['V', 130, 0, 0, 0, 1, 200, 1, 7],
            ['Rnd', 10, 3, 1, 9], ['I', 1], ['E'],
            ['I', 2], ['E'], ['S', 3], ['SG', 1, 11],
            ['I', 4], ['SG', 1, 11],
        ]}]
        self.assertEqual(collect(skills, 100), ([1, 2, 4], [3]))
        self.assertEqual(collect(skills, 200), ([99], []))

    def test_reject_unsafe_script_changes(self):
        for block in [['O', 1], ['V', 129, 1, 0, 200, 0, 0, -1, 0]]:
            with self.assertRaises(ValueError):
                collect([{'name': 'new', 'blocks': [block]}], 100)

    def test_real_demo_keeps_all_opponent_quotes(self):
        skills = read_skills(ROOT / 'assets/demos/ゆい勝ち/script.lton')
        all_images, all_sounds = collect(skills)
        for winner in range(100, 1001, 100):
            images, sounds = collect(skills, winner)
            self.assertLess(len(images), len(all_images) / 2)
            self.assertEqual(sounds, all_sounds)
            # Dialogue skills 8..17: retain every I candidate of this winner.
            # The first winner branches within #8; other roots stop at E.
            dialogue = skills[8 + winner // 100 - 1]['blocks']
            quotes = {b[1] for b in dialogue if b[0] == 'I'}
            self.assertTrue(quotes <= set(images))


if __name__ == '__main__':
    unittest.main()
