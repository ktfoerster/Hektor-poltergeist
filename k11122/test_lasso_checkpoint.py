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
        # Kill a real process after all new generation files are durable but
        # immediately before the pointer replacement. No graceful cleanup runs.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'run'
            code = '''
import os, signal, sys
from pathlib import Path
from test_lasso_checkpoint import CheckpointTests
case = CheckpointTests()
root = Path(sys.argv[1])
cp, save, stats = case.fixture(root)
original = Path.replace
def stop(path, target):
    if path.name == 'current.tmp':
        os.kill(os.getpid(), signal.SIGKILL)
    return original(path, target)
Path.replace = stop
save(1)
'''
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent.resolve()))
            result = subprocess.run([sys.executable, '-c', code, str(root)], env=env,
                                    timeout=10, capture_output=True, text=True)
            self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
            self.assertEqual(audit(root)['witnesses'], 0)
            result = run(Path(temp)/'resumed', 4, 3, -1, [41], 1, resume=root)
            self.assertEqual(result['inherited_witnesses'], 0)
            self.assertEqual(audit(Path(temp)/'resumed')['status'], 'CHECKED')

    def test_invalid_interval(self):
        with tempfile.TemporaryDirectory() as temp:
            for value in (-1, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    run(Path(temp)/'invalid', 4, 3, -1, [41], 1,
                        checkpoint_seconds=value)


if __name__ == '__main__':
    unittest.main()
