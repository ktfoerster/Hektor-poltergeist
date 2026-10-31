"""Merge unconditional residual obligations, never branch assertions or policies."""
import argparse
import hashlib
import json
import pathlib

MODEL = 'static-undirected/common-source-local/two-state'
LATEST = pathlib.Path(__file__).parent / 'checkpoints/run-41176610833'
BACKENDS = {'python-sat==1.8.dev24/Cadical195',
            'python-sat==1.8.dev24/MapleChrono',
            'python-sat==1.8.dev24/Glucose42'}

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
        workflow = provenance.get('workflow_run', {})
        if (provenance.get('checkpoint_file') != path.name or
                type(provenance.get('id')) is not int or provenance['id'] <= 0 or
                type(workflow.get('id')) is not int or workflow['id'] <= 0 or
                not isinstance(workflow.get('head_sha'), str) or
                len(workflow['head_sha']) != 40):
            raise ValueError('invalid checkpoint provenance')
        cp = json.loads(raw)
        if (cp.get('schema') not in (2, 3) or cp.get('target') != target or
                cp.get('model') != MODEL or cp.get('partition', {}).get('branch') != branch):
            raise ValueError('checkpoint model/target/branch mismatch')
        if cp.get('schema') == 3 and cp.get('backend') not in BACKENDS:
            raise ValueError('checkpoint backend mismatch')
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
                        'artifact_id': provenance['id'],
                        'workflow_run_id': workflow['id'],
                        'head_sha': workflow['head_sha'], 'count': len(current),
                        'source_sha256': cp.get('source_sha256')})
    return {'schema': 3, 'target': target, 'model': MODEL,
            'status': 'UNKNOWN', 'partition': None, 'masks': sorted(masks),
            'sources': sources, 'intersection_count': len(sets[0] & sets[1]),
            'scope': 'Union of unconditional live-edge residual obligations only; no policy or branch assertion imported.'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--target', type=int, choices=[0, 3], required=True)
    p.add_argument('--root', type=pathlib.Path, default=LATEST)
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

