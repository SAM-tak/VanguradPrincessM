import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
from gen_script import block, lton_list
from restore_shake import restore


class ShakeConversionTest(unittest.TestCase):
    def test_eb_retains_both_axes_and_color_flags(self):
        raw = dict(type='EB', fadingType=1, rgba=dict(r=2, g=3, b=4, a=5), duration=6,
                   player=True, enemy=False, bg=True, system=False,
                   shakeBgX=dict(type=2, shake=9, duration=10),
                   shakeBgY=dict(type=3, shake=12, duration=13))
        self.assertEqual(block(raw), ['EB', 1, 2, 3, 4, 5, 6, 2, 9, 10, 3, 12, 13, 'player bg'])

    def test_restoration_preserves_branches_and_is_idempotent(self):
        old = ['EB', 0, 0, 0, 0, 0, 0, '']
        new = old[:7] + [1, 3, 9, 2, 8, 12] + old[7:]
        text = '{ name = "attack", level = 10, blocks = {\n    ' + lton_list(old) + ',\n    { "SG", 213, 9 },\n} },\n'
        expected = text.replace(lton_list(old), lton_list(new))
        output, count = restore(text, {'attack': [[new]]}, {})
        self.assertEqual((output, count), (expected, 1))
        self.assertEqual(restore(output, {'attack': [[new]]}, {}), (output, 0))

    def test_ambiguous_source_is_rejected(self):
        old = ['EB', 0, 0, 0, 0, 0, 0, '']
        one = old[:7] + [1, 3, 9, 2, 8, 12] + old[7:]
        two = old[:7] + [1, 30, 9, 2, 8, 12] + old[7:]
        text = '{ name = "attack", level = 10, blocks = {\n    ' + lton_list(old) + ',\n} },\n'
        with self.assertRaisesRegex(ValueError, 'expected one'):
            restore(text, {'attack': [[one], [two]]}, {})

    def test_common_helper_uses_yui_not_owner(self):
        old = ['EB', 0, 0, 0, 0, 0, 0, '']
        new = old[:7] + [3, 2, 4, 0, 0, 0] + old[7:]
        text = '{ name = "共通サポート補助_353_impact", level = 10, blocks = {\n    ' + lton_list(old) + ',\n} },\n'
        output, count = restore(text, {}, {'#353': [[new]]})
        self.assertEqual(count, 1)
        self.assertIn(lton_list(new), output)


if __name__ == '__main__':
    unittest.main()
