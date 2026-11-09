import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

p = Path(__file__).resolve().parents[1] / 'scripts/compact_skill_patch.py'
spec = importlib.util.spec_from_file_location('compact_skill_patch', p)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

class CompactSkillPatchTest(unittest.TestCase):
    def test_patch_is_idempotent_and_keeps_names(self):
        fixture = 'import os\ndef render(skills_by_category, compact_categories):\n' + patcher.OLD + '    return demoted\n\ndef note():\n    return (\n' + patcher.OLD_NOTE + '        "normally")\n'
        with TemporaryDirectory() as directory:
            p = Path(directory) / 'renderer.py'
            p.write_text(fixture, encoding='utf-8')
            self.assertTrue(patcher.apply(p))
            self.assertFalse(patcher.apply(p))
            namespace = {}
            exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'), namespace)
            from unittest.mock import patch
            with patch.dict('os.environ', {'QUATRO_COMPACT_SKILLS': '1'}):
                self.assertEqual(namespace['render']({'one': [], 'two': []}, None), {'one', 'two'})
            with patch.dict('os.environ', {'QUATRO_COMPACT_SKILLS': '0'}):
                self.assertEqual(namespace['render']({'one': [], 'two': []}, {'one'}), {'one'})

    def test_refuses_to_patch_an_unknown_version(self):
        with TemporaryDirectory() as directory:
            p = Path(directory) / 'renderer.py'
            p.write_text('unexpected source', encoding='utf-8')
            with self.assertRaises(ValueError): patcher.apply(p)
            self.assertEqual(p.read_text(encoding='utf-8'), 'unexpected source')

if __name__ == '__main__': unittest.main()
