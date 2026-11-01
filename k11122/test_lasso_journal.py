"""Independent, solver-free regression tests for crash-safe journal checkpoints."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from lasso_journal import Journal, check_committed, iter_committed_lines, lock_directory
from lasso_witness import base_clauses, checked_clause, selector_rows, sha, trace


class MinimalEncoding:
    """Only the recorded DIMACS interface; NO SAT backend used by these tests."""
    def __init__(self, directory, rows):
        self.body_path = directory / 'clauses.body'
        self.body = self.body_path.open('wb')
        self.top = sum(map(len, rows.values()))
        self.clause_count = 0
        self.fingerprint = hashlib.sha256()
        self.backend = 'fixture'
        self.seed = 1

    def add_clause(self, clause):
        raw = (' '.join(map(str, clause)) + ' 0\n').encode()
        self.body.write(raw)
        self.fingerprint.update(raw)
        self.clause_count += 1


class JournalTests(unittest.TestCase):
    def fixture(self, root, witness=True):
        n, target, branch = 4, 3, -1
        rows = selector_rows(n, target)
        (root / 'selectors.json').write_text(json.dumps(
            [[*key, choices] for key, choices in rows.items()]) + '\n')
        (root / 'masks.json').write_text('[41]\n')
        encoder = MinimalEncoding(root, rows)
        for clause in base_clauses(n, target, branch, rows):
            encoder.add_clause(clause)
        recorder = (root / 'witnesses.jsonl').open('wb')
        journal = Journal(root, n, target, branch, [41], {'fixture': 'fixed'}, {})
        journal.commit(encoder, recorder, 0, {'status': 'UNKNOWN'})
        if witness:
            policy = {key: choices[0][0] for key, choices in rows.items()}
            w = trace(policy, n, target, 41, 0)
            self.assertIsNotNone(w)
            item = {'witness': w, 'clause': checked_clause(w, n, target, rows)}
            encoder.add_clause(item['clause'])
            journal.append(recorder, item)
            journal.commit(encoder, recorder, 1, {'status': 'UNKNOWN'})
        return encoder, recorder, journal

    def test_exact_reconstruction_and_partial_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enc, record, journal = self.fixture(root)
            self.assertEqual(check_committed(root)['verified_witnesses'], 1)
            enc.body.write(b'99999 -99999 0\n')
            record.write(b'{broken json uncommitted')
            enc.body.flush()
            record.flush()
            result = check_committed(root)
            self.assertEqual(result['uncommitted_body_bytes'], len(b'99999 -99999 0\n'))
            self.assertEqual(result['uncommitted_witness_bytes'], len(b'{broken json uncommitted'))
            meta = result['metadata']
            lines = list(iter_committed_lines(root, meta['witness_bytes']))
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])['witness']['source'], 0)
            enc.body.close()
            record.close()

    def test_reject_corrupted_committed_prefix_even_if_rehashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enc, record, journal = self.fixture(root)
            enc.body.close()
            record.close()
            path = root / 'witnesses.jsonl'
            item = json.loads(path.read_text())
            item['clause'] = [-1]
            path.write_text(json.dumps(item, sort_keys=True, separators=(',', ':')) + '\n')
            metadata = json.loads((root / 'journal.json').read_text())
            metadata['witness_bytes'] = path.stat().st_size
            metadata['witness_sha256'] = sha(path)
            (root / 'journal.json').write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'invalid or repeated'):
                check_committed(root)

    def test_reject_torn_committed_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enc, record, _ = self.fixture(root)
            enc.body.close()
            record.close()
            with (root / 'witnesses.jsonl').open('r+b') as f:
                f.truncate(f.seek(0, 2) - 2)
            with self.assertRaises(ValueError):
                check_committed(root)

    def test_nonblocking_owner_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = lock_directory(root)
            try:
                with self.assertRaisesRegex(RuntimeError, 'active owner'):
                    lock_directory(root)
            finally:
                lock.close()
            next_lock = lock_directory(root)
            next_lock.close()

    def test_initial_commit_and_empty_witness_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enc, record, _ = self.fixture(root, witness=False)
            enc.body.close()
            record.close()
            x = check_committed(root)
            self.assertEqual(x['verified_witnesses'], 0)
            self.assertEqual(x['metadata']['commits'], 1)


if __name__ == '__main__':
    unittest.main()
