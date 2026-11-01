"""Bounded checkpoint comparison; run separately for old and new source trees.

Uses the exact merged suite, seed, solver and C++ binary. Wrappers time the
original implementation without changing its source or checkpoint frequency.
Full output bundles stay outside git; JSON reports include their hashes.
"""
import argparse
import importlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=15)
    p.add_argument('--interval', type=float)
    p.add_argument('--module', choices=('lasso_search', 'lasso_generation_search'),
                   default='lasso_search')
    a = p.parse_args()
    sys.path.insert(0, str(a.source.resolve() / 'k11122'))
    search = importlib.import_module(a.module)
    from lasso_witness import sha
    import pysat
    from merge_checkpoints import merge, LATEST
    suite = merge(LATEST, 0)
    metrics = dict(snapshot_seconds=0.0, snapshot_hash_seconds=0.0,
                   policy_seconds=0.0, audit_seconds=0.0, snapshots=0)
    in_snapshot = False
    original_sha = search.sha
    def timed_sha(path):
        before = time.monotonic()
        try:
            return original_sha(path)
        finally:
            if in_snapshot:
                metrics['snapshot_hash_seconds'] += time.monotonic() - before
    search.sha = timed_sha
    original_snapshot = search.snapshot
    def timed_snapshot(*args, **kwargs):
        nonlocal in_snapshot
        before = time.monotonic()
        in_snapshot = True
        try:
            return original_snapshot(*args, **kwargs)
        finally:
            in_snapshot = False
            metrics['snapshots'] += 1
            metrics['snapshot_seconds'] += time.monotonic() - before
    search.snapshot = timed_snapshot
    def timed(function, key):
        def invoke(*args, **kwargs):
            before = time.monotonic()
            try:
                return function(*args, **kwargs)
            finally:
                metrics[key] += time.monotonic() - before
        return invoke
    search.audit = timed(search.audit, 'audit_seconds')
    search.checked_policy = timed(search.checked_policy, 'policy_seconds')
    search.write_policy = timed(search.write_policy, 'policy_seconds')
    kwargs = {} if a.interval is None else {'checkpoint_seconds': a.interval}
    before = time.monotonic()
    stats = search.run(a.output, 7, 0, 0, suite['masks'], a.seconds,
                       seed=20261101, backend='cadical195', walker='cpp',
                       batch_binary=a.binary, imported={'sources': suite['sources']},
                       **kwargs)
    report = dict(stats=stats, measured=metrics, total_seconds=time.monotonic()-before,
                  source_commit=subprocess.check_output(
                      ['git', '-C', str(a.source), 'rev-parse', 'HEAD'], text=True).strip(),
                  source_sha256=search.source_hashes(), python=sys.version,
                  platform=platform.platform(), pysat=pysat.__version__,
                  masks=len(suite['masks']), seed=20261101, target=0, branch=0,
                  masks_sha256=sha(a.output/'masks.json'),
                  binary_sha256=sha(a.binary),
                  formula_sha256=sha(a.output/'formula.cnf'),
                  witnesses_sha256=sha(a.output/'witnesses.jsonl'),
                  audit=json.loads((a.output/'audit.json').read_text()))
    (a.output/'benchmark.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
