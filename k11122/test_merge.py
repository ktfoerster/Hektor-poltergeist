import hashlib
import json
import pathlib
import shutil
import tempfile
import unittest
from merge_checkpoints import merge

ROOT = pathlib.Path(__file__).parent / 'checkpoints/run-41168770051'

class MergeTests(unittest.TestCase):
    def test_exact_union_and_no_branch_leak(self):
        for target in (0, 3):
            merged = merge(ROOT, target)
            inputs = [set(json.loads((ROOT / f't{target}-b{b}.json').read_text())['masks']) for b in (0, 1)]
            self.assertEqual(merged['masks'], sorted(inputs[0] | inputs[1]))
            self.assertEqual(merged['intersection_count'], len(inputs[0] & inputs[1]))
            self.assertIsNone(merged['partition'])
            self.assertEqual(merged['status'], 'UNKNOWN')
            self.assertNotIn('last_candidate', merged)
            self.assertEqual(merged['schema'], 3)
            self.assertTrue(all(source['workflow_run_id'] == 41168770051
                                for source in merged['sources']))

    def test_corruption_and_mismatches_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / 'inputs'
            shutil.copytree(ROOT, root)
            p = root / 't0-b0.json'
            original = p.read_bytes()
            p.write_bytes(original + b' ')
            with self.assertRaises(ValueError): merge(root, 0)
            for field, value in [('target', 3), ('model', 'wrong'),
                                 ('backend', 'wrong'), ('masks', [True]),
                                 ('masks', [1 << 19]), ('masks', [1, 1])]:
                cp = json.loads(original); cp[field] = value
                p.write_text(json.dumps(cp))
                q = root / 't0-b0-provenance.json'
                provenance = json.loads(q.read_text())
                provenance['checkpoint_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
                q.write_text(json.dumps(provenance))
                with self.assertRaises(ValueError): merge(root, 0)

if __name__ == '__main__': unittest.main()
