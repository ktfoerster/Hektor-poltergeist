"""Cross-language differential and corruption tests of the accelerated scanner.

The Python lasso-witness checker remains the independent trusted translation.
"""
import json
import random
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from lasso_witness import checked_clause, geometry, selector_rows, trace


class CppBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('g++'):
            raise unittest.SkipTest('g++ unavailable')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.binary = Path(cls.tmp.name) / 'lasso_batch'
        subprocess.run(['g++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        str(Path(__file__).with_name('lasso_batch.cpp')), '-o', str(cls.binary)],
                       check=True, timeout=30, capture_output=True)

    @staticmethod
    def policy(n, target, rng):
        return {key: rng.choice(choices)[0]
                for key, choices in selector_rows(n, target).items()}

    def scanner(self, n, target, policy, masks, limit=2048, mutate=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            table = root / 'policy.tsv'
            table.write_text(f'{n} {target}\n' + ''.join(
                ' '.join(map(str, (*key, action))) + '\n'
                for key, action in sorted(policy.items())))
            residuals = root / 'masks.txt'
            residuals.write_text(''.join(f'{mask}\n' for mask in masks))
            if mutate:
                mutate(table, residuals)
            result = subprocess.run([str(self.binary), str(table), str(residuals), str(limit)],
                                    text=True, capture_output=True, timeout=10)
            if result.returncode:
                return result.returncode, result.stderr
            return 0, [json.loads(line) for line in result.stdout.splitlines()]

    def test_differential_full_scans_both_orbits_and_tiny_graphs(self):
        rng = random.Random(20261101)
        for n, target, trials, size in [(3, 0, 12, 8), (4, 3, 12, 64),
                                        (7, 0, 10, 120), (7, 3, 10, 120)]:
            edge_count = n * (n - 1) // 2 - (2 if n == 7 else 0)
            for i in range(trials):
                policy = self.policy(n, target, rng)
                masks = sorted(rng.sample(range(1 << edge_count), size))
                code, records = self.scanner(n, target, policy, masks)
                self.assertEqual(code, 0, records)
                summary = records[-1]
                self.assertEqual(summary['type'], 'summary')
                self.assertTrue(summary['scan_complete'])
                self.assertEqual(summary['scanned_masks'], size)
                self.assertEqual(summary['total_masks'], size)
                failing = []
                obligations = 0
                for mask in masks:
                    live, reachable = geometry(n, target, mask)
                    obligations += len(reachable) - 1
                    for source in range(n):
                        if trace(policy, n, target, mask, source) is not None:
                            failing.append(mask)
                            break
                self.assertEqual(summary['connected_source_obligations'], obligations)
                self.assertEqual(summary['failed_masks'], len(failing))
                seen = set()
                for item in records[:-1]:
                    self.assertEqual(item['type'], 'witness')
                    w = item['witness']
                    self.assertIn(w['mask'], failing)
                    self.assertEqual(w, trace(policy, n, target, w['mask'], w['source']))
                    clause = tuple(checked_clause(w, n, target))
                    self.assertNotIn(clause, seen)
                    seen.add(clause)
                self.assertEqual(summary['witnesses'], len(seen))

    def test_duplicate_witness_dedup_and_prefix(self):
        n, target = 7, 0
        rng = random.Random(1)
        p = self.policy(n, target, rng)
        masks = list(range(192))
        code, data = self.scanner(n, target, p, masks, 8)
        self.assertEqual(code, 0, data)
        seen = set()
        for item in data[:-1]:
            w = item['witness']
            clause = tuple(checked_clause(w, n, target))
            self.assertNotIn(clause, seen)
            seen.add(clause)
            self.assertEqual(w['steps'][0][:4], [w['source'],
                geometry(n, target, w['mask'])[0][w['source']], -1, 0])

    def test_corrupted_policy_and_masks_rejected(self):
        n, target = 4, 3
        policy = self.policy(n, target, random.Random(17))
        corruptions = [
            lambda p, m: m.write_text('41\n41\n'),
            lambda p, m: m.write_text('41\n40\n'),
            lambda p, m: m.write_text('64\n'),
            lambda p, m: m.write_text('x\n'),
            lambda p, m: p.write_text('4 3\n'),
            lambda p, m: p.write_text(p.read_text() + '0 2 -1 0 2\n'),
            lambda p, m: p.write_text(p.read_text().replace('4 3\n','7 0\n',1)),
        ]
        for mutate in corruptions:
            code, error = self.scanner(n, target, policy, [41], mutate=mutate)
            self.assertNotEqual(code, 0)
            self.assertTrue(error)


    def test_live_cpp_solver_and_audited_cross_version_resume(self):
        try:
            from lasso_search import run
            from lasso_witness import audit, sha
        except ModuleNotFoundError:
            raise unittest.SkipTest('pinned SAT backend unavailable')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / 'first'
            report = run(first, 4, 3, -1, [41], 1.5,
                         walker='cpp', batch_binary=self.binary)
            self.assertIn(report['status'], (
                'UNKNOWN', 'UNSAT_UNCERTIFIED', 'FINITE_SUITE_SAT_UNVERIFIED'))
            self.assertEqual(audit(first)['status'], 'CHECKED')
            # Simulate an old source version while preserving the exact
            # independently audited formula, witness files and policy domain.
            manifest = first / 'manifest.json'
            old = json.loads(manifest.read_text())
            old['source_sha256']['lasso_search.py'] = '0' * 64
            manifest.write_text(json.dumps(old))
            self.assertEqual(audit(first)['status'], 'CHECKED')
            with self.assertRaises(ValueError):
                run(root / 'reject', 4, 3, -1, [41], 1,
                    walker='cpp', batch_binary=self.binary, resume=first)
            migrated = root / 'migrated'
            run(migrated, 4, 3, -1, [41], 1.5,
                walker='cpp', batch_binary=self.binary, resume=first,
                allow_audited_migration=True)
            self.assertEqual(audit(migrated)['status'], 'CHECKED')
            provenance = json.loads((migrated / 'manifest.json').read_text())
            self.assertEqual(provenance['imported']['resumed_from']['manifest_sha256'],
                             sha(manifest))
            self.assertIn('independently rechecked',
                          provenance['imported']['resumed_from']['migration'])



if __name__ == '__main__':
    unittest.main()
