"""Crash-safe append-only K11122 lasso checkpoints, independently replayable.

The committed byte prefixes are a proof ledger; suffixes after interruption are
uncommitted and NEVER imported. A final DIMACS/manifest is still checked by the
unchanged lasso_witness.audit. No SAT solver state is claimed to be checkpointed.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path

from lasso_witness import base_clauses, checked_clause, geometry, selector_rows, sha


def lock_directory(path):
    """Return an owned nonblocking lock handle; do not interfere with an owner."""
    path = Path(path)
    handle = (path / '.owner.lock').open('a+b')
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise RuntimeError('K11122 work directory has an active owner') from None
    return handle


def _sync_file(handle):
    handle.flush()
    os.fsync(handle.fileno())


def _atomic_json(path, object_):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(object_, f, sort_keys=True, indent=2)
        f.write('\n')
        _sync_file(f)
    os.replace(tmp, path)
    # On POSIX fsync the containing directory so the rename survives a crash.
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Journal:
    """Incremental SHA-256 over exactly the persisted witness byte stream."""

    def __init__(self, output, n, target, branch, masks, sources, imported):
        self.output = Path(output)
        self.n, self.target, self.branch = n, target, branch
        self.masks = masks
        self.sources = sources
        self.imported = imported
        self.witness_digest = hashlib.sha256()
        self.witness_count = 0
        self.commits = 0

    def append(self, records, item):
        data = (json.dumps(item, sort_keys=True, separators=(',', ':')) + '\n').encode('utf8')
        records.write(data)
        self.witness_digest.update(data)
        self.witness_count += 1

    def commit(self, encoder, records, witness_count, progress):
        if self.witness_count != witness_count:
            raise RuntimeError('journal witness count does not match CNF')
        _sync_file(encoder.body)
        _sync_file(records)
        body_size, witness_size = encoder.body.tell(), records.tell()
        meta = dict(schema=1, encoding='source-reachable-lasso-journal-v1',
                    n=self.n, target=self.target, branch=self.branch,
                    masks=len(self.masks), variables=encoder.top,
                    clauses=encoder.clause_count, witnesses=witness_count,
                    clause_body_bytes=body_size, witness_bytes=witness_size,
                    clause_body_sha256=encoder.fingerprint.hexdigest(),
                    witness_sha256=self.witness_digest.hexdigest(),
                    masks_sha256=sha(self.output / 'masks.json'),
                    selectors_sha256=sha(self.output / 'selectors.json'),
                    source_sha256=self.sources, imported=self.imported,
                    backend=encoder.backend, seed=encoder.seed,
                    progress=dict(progress), commits=self.commits + 1,
                    scope='frozen finite residual suite; not a solver-memory snapshot')
        _atomic_json(self.output / 'journal.json', meta)
        self.commits += 1
        return meta


def check_committed(directory):
    """Read and independently reconstruct the exact committed clause prefixes.

    A corrupted committed prefix raises, even if its digest is forged in the
    journal. Uncommitted trailing bytes are returned as diagnostics, never used.
    """
    root = Path(directory)
    meta = json.loads((root / 'journal.json').read_text())
    if meta.get('schema') != 1 or meta.get('encoding') != 'source-reachable-lasso-journal-v1':
        raise ValueError('wrong journal schema')
    n, target, branch = meta['n'], meta['target'], meta['branch']
    if type(branch) is not int or branch not in (-1, 0, 1):
        raise ValueError('invalid branch')
    geometry(n, target, 0)
    for name, key in [('masks.json', 'masks_sha256'),
                      ('selectors.json', 'selectors_sha256')]:
        if sha(root / name) != meta[key]:
            raise ValueError('journal dependency digest mismatch: ' + name)
    masks = json.loads((root / 'masks.json').read_text())
    if (not isinstance(masks, list) or not masks or masks != sorted(set(masks))
            or any(type(x) is not int for x in masks) or len(masks) != meta['masks']):
        raise ValueError('journal frozen residual domain mismatch')
    for mask in masks:
        geometry(n, target, mask)
    allowed = set(masks)
    rows = selector_rows(n, target)
    expected_map = [[*key, [[act, var] for act, var in choices]]
                    for key, choices in rows.items()]
    if json.loads((root / 'selectors.json').read_text()) != expected_map:
        raise ValueError('journal selector translation mismatch')
    nvars = sum(len(v) for v in rows.values())
    if nvars != meta['variables']:
        raise ValueError('journal variable count mismatch')
    body_path, witnesses_path = root / 'clauses.body', root / 'witnesses.jsonl'
    body_size = meta['clause_body_bytes']
    wit_size = meta['witness_bytes']
    if (any(type(z) is not int or z < 0 for z in (body_size, wit_size, meta['clauses'], meta['witnesses']))
            or body_path.stat().st_size < body_size
            or witnesses_path.stat().st_size < wit_size):
        raise ValueError('truncated or malformed journal offsets')
    body_digest, witness_digest = hashlib.sha256(), hashlib.sha256()
    count, witnesses = 0, 0
    seen_clauses = set()
    with body_path.open('rb') as body, witnesses_path.open('rb') as source:
        def match_clause(clause):
            nonlocal count
            expected = (' '.join(map(str, clause)) + ' 0\n').encode()
            found = body.readline()
            if found != expected or body.tell() > body_size:
                raise ValueError('journal CNF differs from independently reconstructed clauses')
            body_digest.update(found)
            count += 1

        for base in base_clauses(n, target, branch, rows):
            match_clause(base)
        while source.tell() < wit_size:
            raw = source.readline()
            if not raw.endswith(b'\n') or source.tell() > wit_size:
                raise ValueError('torn committed witness line')
            witness_digest.update(raw)
            item = json.loads(raw)
            if (set(item) != {'witness', 'clause'}
                    or item['witness']['mask'] not in allowed):
                raise ValueError('journal witness out of frozen suite')
            clause = checked_clause(item['witness'], n, target, rows)
            if item['clause'] != clause or tuple(clause) in seen_clauses:
                raise ValueError('invalid or repeated necessary witness clause')
            seen_clauses.add(tuple(clause))
            match_clause(clause)
            witnesses += 1
        if source.tell() != wit_size or body.tell() != body_size:
            raise ValueError('journal committed byte prefix mismatch')
    if (count != meta['clauses'] or witnesses != meta['witnesses']
            or body_digest.hexdigest() != meta['clause_body_sha256']
            or witness_digest.hexdigest() != meta['witness_sha256']):
        raise ValueError('journal clause/witness counts or digest mismatch')
    return dict(metadata=meta, verified_clauses=count, verified_witnesses=witnesses,
                uncommitted_body_bytes=body_path.stat().st_size - body_size,
                uncommitted_witness_bytes=witnesses_path.stat().st_size - wit_size)


def iter_committed_lines(directory, bytes_count):
    """Replay exact independently-audited committed witness prefix only."""
    with (Path(directory) / 'witnesses.jsonl').open('rb') as source:
        while source.tell() < bytes_count:
            raw = source.readline()
            if not raw.endswith(b'\n') or source.tell() > bytes_count:
                raise ValueError('committed witness changed during resume')
            yield raw.decode('utf8').rstrip('\n')
        if source.tell() != bytes_count:
            raise ValueError('inconsistent resume offset')
