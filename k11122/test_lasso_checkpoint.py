"""Crash/recovery tests using small certificates, not expensive solving."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lasso_checkpoint import Checkpoints, checkpoint_root
from lasso_search import CapturedPolicy, run, snapshot
from lasso_witness import audit, checked_clause, selector_rows, sha, trace
from test_lasso import tiny_policies


class CheckpointTests(unittest.TestCase):
    def fixture(self, root):
        root.mkdir()
        cp = Checkpoints(root, 5)
        rows = selector_rows(4, 3)
        enc = CapturedPolicy(4, 3, cp.work / 'clauses.body')
        self.addCleanup(enc.close)
        (cp.work / 'selectors.json').write_text(json.dumps(
            [[*key, choices] for key, choices in rows.items()]) + '\n')
        (cp.work / 'masks.json').write_text('[41]\n')
        (cp.work / 'witnesses.jsonl').write_text('')
        stats = dict(status='UNKNOWN', checkpoint_count=0,
                     checkpoint_total_seconds=0.0, checkpoint_publish_seconds=0.0,
                     progress_seconds=0.0)
        def save(count=0, force=True):
            cp.save(enc, [41], 3, -1, count, stats, {}, snapshot, force=force)
        save()
        witness = trace(next(tiny_policies()), 4, 3, 41, 0)
        clause = checked_clause(witness, 4, 3, rows)
        enc.add_clause(clause)
        (cp.work / 'witnesses.jsonl').write_text(json.dumps(
            dict(witness=witness, clause=clause)) + '\n')
        return cp, save, stats

    def test_lightweight_progress_does_not_change_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'run'
            cp, save, stats = self.fixture(root)
            first = checkpoint_root(root)
            save(1, force=False)
            self.assertEqual(checkpoint_root(root), first)
            self.assertEqual(audit(root)['witnesses'], 0)
            self.assertEqual(stats['checkpoint_count'], 1)
            self.assertTrue(json.loads((root/'progress.json').read_text())['advisory'])
            # Even a damaged uncommitted working tail cannot affect recovery.
            (cp.work/'witnesses.jsonl').write_text('{partial')
            (root/'progress.json').write_text('{partial')
            self.assertEqual(audit(root)['witnesses'], 0)

    def test_publication_and_independent_continuation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'run'
            cp, save, stats = self.fixture(root)
            old = checkpoint_root(root)
            old_hash = sha(old/'manifest.json')
            save(1)
            self.assertNotEqual(checkpoint_root(root), old)
            self.assertEqual(audit(root)['witnesses'], 1)
            self.assertEqual(audit(old)['witnesses'], 0)
            self.assertEqual(sha(old/'manifest.json'), old_hash)
            result = run(Path(temp)/'resumed', 4, 3, -1, [41], 1, resume=root)
            self.assertEqual(result['inherited_witnesses'], 1)
            self.assertEqual(audit(Path(temp)/'resumed')['status'], 'CHECKED')

    def test_failures_at_publication_boundaries_preserve_committed_generation(self):
        for phase in ('copy', 'export', 'file_sync', 'rename', 'pointer', 'after_pointer'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'run'
                cp, save, stats = self.fixture(root)
                old = checkpoint_root(root)
                if phase == 'copy':
                    injection = patch('lasso_checkpoint.shutil.copyfile', side_effect=OSError('copy'))
                elif phase == 'export':
                    injection = patch('lasso_search.shutil.copyfileobj', side_effect=OSError('CNF'))
                elif phase == 'file_sync':
                    injection = patch('lasso_checkpoint.os.fsync', side_effect=OSError('sync'))
                elif phase == 'rename':
                    injection = patch.object(Path, 'rename', side_effect=OSError('rename'))
                elif phase == 'pointer':
                    original = Path.replace
                    def fail_pointer(path, target):
                        if path.name == 'current.tmp':
                            raise OSError('pointer')
                        return original(path, target)
                    injection = patch.object(Path, 'replace', fail_pointer)
                else:
                    from lasso_checkpoint import sync_directory
                    def after_pointer(path):
                        if Path(path) == root:
                            raise OSError('after commit')
                        return sync_directory(path)
                    injection = patch('lasso_checkpoint.sync_directory', after_pointer)
                with injection, self.assertRaises(OSError):
                    save(1)
                self.assertEqual(audit(root)['witnesses'], 1 if phase == 'after_pointer' else 0)
                self.assertEqual(audit(old)['witnesses'], 0)

    def test_committed_corruption_and_semantic_tampering_rejected(self):
        for name in ('formula.cnf', 'witnesses.jsonl', 'selectors.json', 'masks.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'run'
                cp, save, stats = self.fixture(root)
                save(1)
                with (root/name).open('a') as f:
                    f.write('corrupt')
                with self.assertRaises(ValueError):
                    audit(root)
                with self.assertRaises(ValueError):
                    run(Path(temp)/'reject', 4, 3, -1, [41], 1, resume=root)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'run'
            cp, save, stats = self.fixture(root)
            save(1)
            item = json.loads((root/'witnesses.jsonl').read_text())
            item['clause'] = [-1]
            (root/'witnesses.jsonl').write_text(json.dumps(item)+'\n')
            meta = json.loads((root/'manifest.json').read_text())
            meta['sha256']['witnesses.jsonl'] = sha(root/'witnesses.jsonl')
            (root/'manifest.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):
                audit(root)

    def test_sigkill_during_pointer_publication(self):
        # Real process deaths before commit, after pointer rename, and after
        # directory fsync: no exception handler or graceful cleanup can run.
        for point in ('before', 'after', 'durable'):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'run'
                code = """
import os, signal, sys
from pathlib import Path
import lasso_checkpoint
from test_lasso_checkpoint import CheckpointTests
case = CheckpointTests()
root = Path(sys.argv[1])
point = sys.argv[2]
cp, save, stats = case.fixture(root)
original = Path.replace
sync = lasso_checkpoint.sync_directory
def stop(path, target):
    if path.name == 'current.tmp' and point == 'before':
        os.kill(os.getpid(), signal.SIGKILL)
    result = original(path, target)
    if path.name == 'current.tmp' and point == 'after':
        os.kill(os.getpid(), signal.SIGKILL)
    return result
def sync_then_stop(path):
    sync(path)
    if path == root and point == 'durable':
        os.kill(os.getpid(), signal.SIGKILL)
Path.replace = stop
lasso_checkpoint.sync_directory = sync_then_stop
save(1)
"""
                env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent.resolve()))
                result = subprocess.run([sys.executable, '-c', code, str(root), point],
                                        env=env, timeout=10, capture_output=True, text=True)
                self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
                expected = 0 if point == 'before' else 1
                self.assertEqual(audit(root)['witnesses'], expected)
                result = run(Path(temp)/'resumed', 4, 3, -1, [41], 1, resume=root)
                self.assertEqual(result['inherited_witnesses'], expected)
                self.assertEqual(audit(Path(temp)/'resumed')['status'], 'CHECKED')

    def test_audit_pins_generation_during_concurrent_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'run'
            cp, save, stats = self.fixture(root)
            original_sha = sha
            published = False
            def publish_then_hash(path):
                nonlocal published
                if not published:
                    published = True
                    save(1)
                return original_sha(path)
            with patch('lasso_witness.sha', publish_then_hash):
                # The audit already pinned the old generation before hashing.
                self.assertEqual(audit(root)['witnesses'], 0)
            self.assertTrue(published)
            self.assertEqual(audit(root)['witnesses'], 1)

    def test_missing_hashes_and_accounting_rejected(self):
        for defect in ('all_hashes', 'formula_hash', 'optional_hash',
                       'mask_count', 'boolean_count', 'clause_count', 'witness_count'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'run'
                cp, save, stats = self.fixture(root)
                (cp.work/'cpp-batches.jsonl').write_text('{}\n')
                save(1)
                manifest = root/'manifest.json'
                meta = json.loads(manifest.read_text())
                if defect == 'all_hashes':
                    meta['sha256'] = {}
                elif defect == 'formula_hash':
                    del meta['sha256']['formula.cnf']
                elif defect == 'optional_hash':
                    del meta['sha256']['cpp-batches.jsonl']
                elif defect == 'mask_count':
                    meta['masks'] = 2
                elif defect == 'boolean_count':
                    meta['witnesses'] = True
                elif defect == 'clause_count':
                    meta['clauses'] += 1
                else:
                    meta['witnesses'] += 1
                manifest.write_text(json.dumps(meta))
                with self.assertRaises(ValueError):
                    audit(root)

    def test_streaming_audit_rejects_rehashed_cnf_edits(self):
        for defect in ('truncated', 'extra', 'reordered', 'changed_literal'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'run'
                cp, save, stats = self.fixture(root)
                save(1)
                formula = root/'formula.cnf'
                lines = formula.read_bytes().splitlines(keepends=True)
                if defect == 'truncated':
                    lines.pop()
                elif defect == 'extra':
                    lines.append(b'1 0\n')
                elif defect == 'reordered':
                    lines[1], lines[2] = lines[2], lines[1]
                else:
                    lines[-1] = b'1 0\n'
                formula.write_bytes(b''.join(lines))
                meta = json.loads((root/'manifest.json').read_text())
                meta['sha256']['formula.cnf'] = sha(formula)
                import hashlib
                meta['clause_body_sha256'] = hashlib.sha256(b''.join(lines[1:])).hexdigest()
                (root/'manifest.json').write_text(json.dumps(meta))
                with self.assertRaises(ValueError):
                    audit(root)

    def test_resume_normalizes_unterminated_last_witness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'run'
            cp, save, stats = self.fixture(root)
            save(1)
            witness = root/'witnesses.jsonl'
            witness.write_text(witness.read_text().rstrip('\n'))
            meta = json.loads((root/'manifest.json').read_text())
            meta['sha256']['witnesses.jsonl'] = sha(witness)
            (root/'manifest.json').write_text(json.dumps(meta))
            self.assertEqual(audit(root)['witnesses'], 1)
            resumed = Path(temp)/'resumed'
            result = run(resumed, 4, 3, -1, [41], 1, resume=root)
            self.assertEqual(result['inherited_witnesses'], 1)
            self.assertTrue((resumed/'witnesses.jsonl').read_bytes().endswith(b'\n'))
            self.assertEqual(audit(resumed)['status'], 'CHECKED')

    def test_verifier_log_integrity(self):
        for defect in ('contents', 'missing_hash'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'run'
                cp, save, stats = self.fixture(root)
                log = cp.work/'exhaustive-verifier.log'
                log.write_text('test verifier transcript; not a proof\n')
                save(1)
                self.assertEqual(audit(root)['status'], 'CHECKED')
                manifest = root/'manifest.json'
                meta = json.loads(manifest.read_text())
                self.assertEqual(meta['sha256']['exhaustive-verifier.log'],
                                 sha(root/'exhaustive-verifier.log'))
                if defect == 'contents':
                    (root/'exhaustive-verifier.log').write_text('corrupted transcript')
                else:
                    del meta['sha256']['exhaustive-verifier.log']
                    manifest.write_text(json.dumps(meta))
                with self.assertRaises(ValueError):
                    audit(root)

    def test_witness_cap_validation_and_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            for cap in (0, -1, True, 1.5):
                with self.assertRaises(ValueError):
                    run(Path(temp)/'invalid', 4, 3, -1, [41], 1, max_new_per_round=cap)
                self.assertFalse((Path(temp)/'invalid').exists())
            out = Path(temp)/'valid'
            summary = run(out, 4, 3, -1, [41], 1, max_new_per_round=1)
            self.assertEqual(summary['max_new_per_round'], 1)
            manifest = json.loads((out/'manifest.json').read_text())
            self.assertEqual(manifest['progress']['max_new_per_round'], 1)
            self.assertEqual(audit(out)['status'], 'CHECKED')

    def test_invalid_interval(self):
        with tempfile.TemporaryDirectory() as temp:
            for value in (-1, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    run(Path(temp)/'invalid', 4, 3, -1, [41], 1,
                        checkpoint_seconds=value)


if __name__ == '__main__':
    unittest.main()
