import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/fm2k_convert'))
from audit_support_variants import Source, alignment, canonical_blocks, clean, compare


class SupportVariantAuditTest(unittest.TestCase):
    @staticmethod
    def source(name, entries):
        from collections import defaultdict
        s = Source.__new__(Source)
        s.name = name
        s.skills = [{'name': n} for n, _ in entries]
        s.blocks = [[clean(b) for b in bs] for _, bs in entries]
        s.names = defaultdict(list)
        for i, (n, _) in enumerate(entries):
            s.names[n].append(i)
        s.media = lambda op, n: 'same-image'
        return s

    def test_renumbering_media_and_skills_does_not_create_a_variant(self):
        a = self.source('ゆい', [('unused', [['E']]),
                                ('support', [['I', 7, 3, 0, 0, ''], ['SG', 2, 0]]),
                                ('helper', [['E']])])
        b = self.source('other', [('unused', [['E']]), ('helper', [['E']]),
                                 ('support', [['I', 9, 3, 0, 0, ''], ['SG', 1, 0]])])
        self.assertEqual(compare(a, b, [1]), [])
        b.blocks[2][0][2] = 4
        rows = compare(a, b, [1])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['changes'][0]['base_range'], [0, 1])

    def test_inactive_operands_are_noise_but_gauge_writes_are_not(self):
        a = ['V', 71, 0, 1, 99, 0, 55, 777, 20]
        self.assertEqual(clean(a), ['Nop'])
        write = ['V', 71, 2, 0, -15, 0, 99, 12, 5]
        self.assertEqual(clean(write)[1:5], [71, 2, 0, -15])
        branch = ['V', 76, 0, 1, 9, 1, 93, 243, 0]
        self.assertEqual(clean(branch)[5:], [1, 93, 243, 0])

    def test_shifted_target_matches_but_inserted_target_is_not_guessed(self):
        a = [['Settings', 10, 0], ['I', 10, 2, 0, 0, ''], ['E']]
        b = [a[0], ['S', 3], a[1], a[2]]
        self.assertEqual(alignment(a, b), {0: 0, 2: 1, 3: 2, 4: 3})

    def test_refs_keep_changed_destinations_and_ignore_reaction_numbers(self):
        class Fixture:
            name = 'test'
            blocks = [[['SG', 9, 3], ['O', 9, 1, 0, 0, 0, 0, 8, 4, 'out'],
                       ['R', 9, 9, 9, 9, 9, 9]]]
        bs = canonical_blocks(Fixture(), 0, {9: 4}, {9: {3: 2}})
        self.assertEqual(bs[0], ['SG', 'skill:4', 2])
        self.assertEqual(bs[1][1:3], ['skill:4', 'local:1'])
        self.assertEqual(bs[1][7], 'unmatched:test:8')
        self.assertEqual(bs[2], Fixture.blocks[0][2])


if __name__ == '__main__':
    unittest.main()
