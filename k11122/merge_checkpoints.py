"""Merge unconditional residual obligations, never branch assertions or policies."""
import argparse
import hashlib
import json
import pathlib

MODEL = 'static-undirected/common-source-local/two-state'

def merge(root, target):
    masks = set()
    sources = []
    sets = []
    for branch in (0, 1):
        path = root / f't{target}-b{branch}.json'
        provenance = json.loads((root / f't{target}-b{branch}-provenance.json').read_text())
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != provenance['checkpoint_sha256']:
            raise ValueError('checkpoint hash mismatch')
        cp = json.loads(raw)
        if (cp.get('schema') != 2 or cp.get('target') != target or
                cp.get('model') != MODEL or cp.get('partition', {}).get('branch') != branch):
            raise ValueError('checkpoint model/target/branch mismatch')
        values = cp.get('masks')
        if (not isinstance(values, list) or not values or
                any(type(m) is not int or not 0 <= m < (1 << 19) for m in values)):
            raise ValueError('invalid residual masks')
        current = set(values)
        if len(current) != len(values):
            raise ValueError('duplicate source masks')
        sets.append(current)
        masks.update(current)
        sources.append({'file': path.name, 'sha256': digest,
                        'artifact_id': provenance['id'], 'count': len(current)})
    return {'schema': 2, 'target': target, 'model': MODEL,
            'status': 'UNKNOWN', 'partition': None, 'masks': sorted(masks),
            'sources': sources, 'intersection_count': len(sets[0] & sets[1]),
            'scope': 'Union of unconditional live-edge residual obligations only; no policy or branch assertion imported.'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--target', type=int, choices=[0, 3], required=True)
    p.add_argument('--root', type=pathlib.Path, default=pathlib.Path(__file__).parent / 'checkpoints/run-41153794470')
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    data = merge(args.root, args.target)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        f.write(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'target': args.target, 'merged_residuals': len(data['masks']),
                      'intersection_count': data['intersection_count']}))

if __name__ == '__main__':
    main()
