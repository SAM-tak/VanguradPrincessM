import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/fm2k_convert'))
from supports import expand_recipe, read_skills, source_script
from support_namespaces import BANKS, ref_positions


def runtime_skills(path, libraries=None):
    text = path.read_text(encoding='utf-8')
    base = re.search(r'^namespaceBase = (\d+)', text, re.M)
    base = int(base[1]) if base else 0
    result = {}
    for part in re.split(r'(?m)^\{ name = ', text)[1:]:
        number = int(re.search(r'\bid = (\d+)', part)[1]) + base
        blocks = [json.loads('[' + line.strip()[1:-2] + ']')
                  for line in part.splitlines()[1:] if line.strip().startswith('{ "')]
        patch = re.search(r'support = "([^"]+)", base = (\d+), recipe = \{([^}]*)\}', part)
        if patch:
            model = libraries[BANKS[patch[1]] + int(patch[2])]
            blocks = expand_recipe(model['blocks'], json.loads('[' + patch[3] + ']'), blocks)
        name = json.loads(re.match(r'("(?:[^"\\]|\\.)*")', part)[1])
        if number in result:
            raise AssertionError(f'Duplicate runtime ID: {path}/{number}')
        result[number] = {'name': name, 'blocks': blocks}
    return result


class SupportNamespacesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT / 'data'
        cls.libraries = {}
        for name in BANKS:
            cls.libraries.update(runtime_skills(cls.root / 'supports' / name / 'script.lton'))

    def test_shared_packages_have_no_character_targets(self):
        self.assertEqual(len(self.libraries), 366)
        for number, skill in self.libraries.items():
            for block in skill['blocks']:
                for k in ref_positions(block):
                    if block[k] > 0:
                        self.assertTrue(block[k] in self.libraries, (number, block))

    def test_compact_owners_and_complete_runtime_graphs(self):
        for path in (self.root / 'characters').glob('*/script.lton'):
            if path.parent.name == 'だみー':
                continue
            own = runtime_skills(path, self.libraries)
            ordinary = {n for n in own if n < 10000}
            self.assertGreaterEqual(len(ordinary), 495)
            if path.parent.name == 'ヒルダ':
                self.assertEqual(len(ordinary), 806)
                self.assertIn('fixedSupport = true^', path.read_text(encoding='utf-8'))
                self.assertEqual(own[451]['blocks'][2], ['SG', 688, 0])
                self.assertIn(['I', 1543, 5, -18, 1000, ''], own[710]['blocks'])
            else:
                self.assertLessEqual(len(ordinary), 499)
            if path.parent.name != 'くるみ':
                self.assertEqual(len(ordinary), len(own))
            graph = self.libraries | own
            # Verify all instruction references in the output that the game reads.
            for number, skill in graph.items():
                for block in skill['blocks']:
                    for k in ref_positions(block):
                        if block[k] > 0:
                            self.assertTrue(block[k] in graph, (path.parent.name, number, block))

    def test_reactions_are_not_skill_references(self):
        self.assertEqual(ref_positions(['R', 402, 404, 405, 406, 407, 452]), [])

    def test_conversion_matches_normalized_semantics(self):
        for path in (self.root / 'characters').glob('*/script.lton'):
            if path.parent.name == 'だみー':
                continue
            original = read_skills(path)
            source = source_script(path).read_text(encoding='utf-8')
            remap = {}
            for i, part in enumerate(re.split(r'(?m)^\{ name = ', source)[1:]):
                ref = re.search(r'support = "([^"]+)", base = (\d+)', part)
                if ref:
                    remap[i] = BANKS[ref[1]] + int(ref[2])
            graph = self.libraries | runtime_skills(path, self.libraries)
            for i, skill in enumerate(original):
                actual = graph[remap.get(i, i)]['blocks']
                self.assertEqual(len(actual), len(skill['blocks']))
                for before, after in zip(skill['blocks'], actual):
                    expected = before[:]
                    for k in ref_positions(before):
                        if before[k] > 0:
                            expected[k] = remap.get(before[k], before[k])
                    self.assertEqual(after, expected, (path.parent.name, i))


if __name__ == '__main__':
    unittest.main()
