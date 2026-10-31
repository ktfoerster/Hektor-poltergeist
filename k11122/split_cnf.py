"""Four-way exhaustive source-action split of a retained parent CNF."""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from proof_cnf import sha, iter_cnf


def plan(root):
    meta = json.loads((root/'export.json').read_text())
    rows = json.loads((root/'selectors.json').read_text())
    assert sha(root/'formula.cnf') == meta['cnf_sha256']
    assert sha(root/'selectors.json') == meta['selectors_sha256']
    excluded = meta['partition']['row'] if meta['partition'] else None
    candidates = [r for r in rows if r[:4] != excluded and r[2] == -1 and len(r[4]) == 4]
    if not candidates:
        raise ValueError('no four-action source row')
    # Prefer a source observation occurring in many retained residuals.
    from sat_search import graph, adjacency
    edges = graph(meta['n'])
    observations = [adjacency(meta['n'], edges, mask) for mask in meta['masks']]
    row = min(candidates, key=lambda r: (-sum(a[r[0]] == r[1] for a in observations), r[:4]))
    return dict(schema=1, parent_sha256=meta['cnf_sha256'], row=row[:4],
                cases=[dict(case=i, action=a, literal=v) for i,(a,v) in enumerate(row[4])],
                coverage='Every action of this exactly-one policy row; disjoint and exhaustive within parent only')


def child(root, output, case):
    split = plan(root)
    if type(case) is not int or not 0 <= case < len(split['cases']):
        raise ValueError('invalid case')
    output.mkdir(parents=True, exist_ok=False)
    meta = json.loads((root/'export.json').read_text())
    with (root/'formula.cnf').open('rb') as source, (output/'formula.cnf').open('wb') as dest:
        header = source.readline().decode().split()
        if header != ['p','cnf',str(meta['variables']),str(meta['clauses'])]:
            raise ValueError('header mismatch')
        dest.write(f"p cnf {meta['variables']} {meta['clauses']+1}\n".encode())
        shutil.copyfileobj(source,dest)
        dest.write(f"{split['cases'][case]['literal']} 0\n".encode())
    for name in ['selectors.json','export.json']:
        shutil.copyfile(root/name, output/('parent-'+name))
    split['selected_case'] = case
    split['child_sha256'] = sha(output/'formula.cnf')
    (output/'split.json').write_text(json.dumps(split,indent=2,sort_keys=True))
    return split


def decode(root):
    meta=json.loads((root/'parent-export.json').read_text())
    split=json.loads((root/'split.json').read_text())
    assert sha(root/'formula.cnf') == split['child_sha256']
    assert sha(root/'parent-selectors.json') == meta['selectors_sha256']
    model=json.loads((root/'model.json').read_text())
    if any(type(v) is not int or v == 0 for v in model) or len(set(map(abs,model))) != len(model):
        raise ValueError('invalid model')
    assigned=set(model)
    for clause in iter_cnf(root/'formula.cnf'):
        if not clause & assigned:
            raise ValueError('model fails CNF')
    rows=[]
    for row in json.loads((root/'parent-selectors.json').read_text()):
        selected=[action for action,var in row[4] if var in assigned]
        if len(selected)!=1:
            raise ValueError('selector mismatch')
        rows.append([*row[:4],selected[0]])
    (root/'candidate.tsv').write_text(f"{meta['n']} {meta['target']}\n"+''.join(' '.join(map(str,r))+'\n' for r in rows))
    binary=root/'verify'
    subprocess.run(['g++','-O3','-std=c++17',str(pathlib.Path(__file__).with_name('verify.cpp')),'-o',str(binary)],check=True,timeout=120)
    replay=subprocess.run([str(binary.resolve()),str((root/'candidate.tsv').resolve())],capture_output=True,text=True,check=True,timeout=180)
    audit=json.loads(replay.stdout)
    if meta['n']==7 and (audit['masks']!=524288 or audit['obligations']!={0:2979236,3:2937186}[meta['target']]):
        raise ValueError('incomplete replay')
    audit['candidate_sha256']=sha(root/'candidate.tsv')
    audit['status']='FULL_ORBIT_VERIFIED' if audit['failures']==0 else 'FINITE_SAT_GLOBALLY_INVALID'
    (root/'routing-replay.json').write_text(json.dumps(audit,indent=2,sort_keys=True))
    print(json.dumps(audit))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['split','decode'])
    p.add_argument('--root',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path)
    p.add_argument('--case',type=int)
    a=p.parse_args()
    if a.mode=='split':
        child(a.root,a.output,a.case)
    elif json.loads((a.root/'certification.json').read_text())['status']=='SAT_FINITE_CNF':
        decode(a.root)
