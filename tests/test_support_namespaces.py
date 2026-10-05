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
    def test_owner_packages_preserve_original_blocks_and_targets(self):
        from owner_supports import groups_for, owner_hook
        root = ROOT / 'data'
        for path in (root / 'characters').glob('*/script.lton'):
            owner = path.parent.name
            if owner in ('だみー', 'ヒルダ'):
                continue
            original = read_skills(path)
            groups = groups_for(original)
            core_map = {n: BANKS[name]+n for name, ns in groups.items() for n in ns}
            body = runtime_skills(path)
            self.assertEqual(set(body), set(range(len(original))) - set(core_map))
            for n, skill in body.items():
                expected = []
                for raw in original[n]['blocks']:
                    b = raw[:]
                    for k in ref_positions(b):
                        b[k] = core_map.get(b[k], b[k])
                    expected.append(b)
                self.assertEqual(skill['blocks'], expected, (owner, n))
            graph = dict(body)
            for name, ns in groups.items():
                package = root / 'supports' / name / f'{owner}.lton'
                text = package.read_text(encoding='utf-8')
                self.assertNotIn('recipe =', text)
                self.assertIn(f'media = "assets/characters/{owner}"', text)
                own = runtime_skills(package)
                self.assertFalse(set(own) & set(graph))
                graph.update(own)
                helpers = {n-BANKS[name]: n for n in own if n-BANKS[name] not in ns}
                mapping = core_map | helpers
                selected_graph = body | own
                for handle, skill in own.items():
                    for b in skill['blocks']:
                        for k in ref_positions(b):
                            if b[k] > 0:
                                self.assertTrue(b[k] in selected_graph, (owner, name, handle, b))
                for handle, skill in own.items():
                    raw_id = handle - BANKS[name]
                    self.assertEqual(len(skill['blocks']), len(original[raw_id]['blocks']))
                    for at, (raw, actual) in enumerate(zip(original[raw_id]['blocks'], skill['blocks'])):
                        if raw_id not in ns and actual == ['Nop']:
                            continue
                        expected = raw[:]
                        if not (owner == 'くるみ' and owner_hook(raw) and raw[7] not in core_map):
                            for k in ref_positions(expected):
                                expected[k] = mapping.get(expected[k], expected[k])
                        self.assertEqual(expected, actual, (owner, name, raw_id, at))
            for n, skill in graph.items():
                for b in skill['blocks']:
                    for k in ref_positions(b):
                        if b[k] > 0:
                            self.assertTrue(b[k] in graph, (owner, n, b))
                            # Original data also jumps beyond a skill's end.
                            # Keep that termination behavior rather than clamp it.

    def test_real_owner_balance_values_and_voice_entry(self):
        root = ROOT / 'data/supports'
        powers = {'ゆい': 50, 'かえで': 30, 'えり': 35, 'あやね': 20, 'くるみ': 70}
        for owner, power in powers.items():
            skills = runtime_skills(root / 'えこ' / f'{owner}.lton')
            kick = next(s for s in skills.values() if s['name'] == 'キック')
            hit = next(b for b in kick['blocks'] if b[0:2] == ['FA', 0] and b[4] > 0)
            self.assertEqual(hit[6], power)
        eri = runtime_skills(root / 'シエラ/えり.lton')
        helper = eri[20353]['blocks']
        self.assertEqual(helper[3], ['E'])
        self.assertNotIn(['S', 29], helper)
        movement = next(s for s in eri.values() if s['name'] == 'サポート移動前')
        self.assertTrue(any(b[:3] == ['O', 20353, 3] for b in movement['blocks']))
        self.assertIn(['V', 71, 2, 0, -15, 0, 0, -1, 0], eri[20404]['blocks'])

    def test_reactions_are_not_skill_references(self):
        self.assertEqual(ref_positions(['R', 402, 404, 405, 406, 407, 452]), [])

    def test_regeneration_is_identical(self):
        from owner_supports import plan
        outputs, _ = plan(ROOT / 'data')
        for path, text in outputs.items():
            self.assertEqual(path.read_text(encoding='utf-8'), text, str(path))


if __name__ == '__main__':
    unittest.main()
