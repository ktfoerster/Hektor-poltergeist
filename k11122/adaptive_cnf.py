"""Bounded, resumable exhaustive CNF splitting. Probes never certify UNSAT."""
import argparse
import fcntl
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
from proof_cnf import sha, iter_cnf, check, solve
from split_cnf import plan, decode

HERE = pathlib.Path(__file__).resolve().parent


def read(p):
    return json.loads(pathlib.Path(p).read_text())


def write(p, value):
    p = pathlib.Path(p)
    tmp = p.with_suffix(p.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def formula(base, dest, assumptions):
    meta = read(base/'export.json')
    with (base/'formula.cnf').open('rb') as src, dest.open('wb') as out:
        header = src.readline().decode().split()
        if header != ['p', 'cnf', str(meta['variables']), str(meta['clauses'])]:
            raise ValueError('parent header mismatch')
        out.write(f"p cnf {meta['variables']} {meta['clauses']+len(assumptions)}\n".encode())
        shutil.copyfileobj(src, out)
        for lit in assumptions:
            out.write(f'{lit} 0\n'.encode())


def new_node(work, ledger, key, assumptions):
    folder = work/'nodes'/key
    # An interrupted transaction may have left an unreferenced directory.
    # Reuse only an exact reconstruction, never a stale result directory.
    if key in ledger['nodes']:
        raise ValueError('node already committed')
    if folder.exists():
        orphan=work/'orphans';orphan.mkdir(exist_ok=True)
        folder.rename(orphan/(key+'-'+str(time.time_ns())))
    folder.mkdir(parents=True)
    formula(work/'parent', folder/'formula.cnf', assumptions)
    write(folder/'assumptions.json',assumptions)
    node = dict(assumptions=assumptions, status='PENDING', attempts=[],
                cnf_sha256=sha(folder/'formula.cnf'), children=[])
    ledger['nodes'][key] = node
    return node


def initialize(parent, work):
    meta = read(parent/'export.json')
    if sha(parent/'formula.cnf') != meta['cnf_sha256'] or sha(parent/'selectors.json') != meta['selectors_sha256']:
        raise ValueError('stale parent')
    split = plan(parent)
    work.mkdir(parents=True, exist_ok=False)
    shutil.copytree(parent, work/'parent')
    ledger = dict(schema=1, parent_sha256=meta['cnf_sha256'],
                  metadata_sha256=sha(parent/'export.json'),
                  selectors_sha256=meta['selectors_sha256'],
                  source_sha256={n:sha(HERE/n) for n in ['adaptive_cnf.py','proof_cnf.py','rup_watch.py','split_cnf.py','verify.cpp']},
                  scope='finite family / target and original branch only', nodes={})
    root = new_node(work, ledger, 'r', [])
    root.update(status='SPLIT', split_literals=[c['literal'] for c in split['cases']], split_kind='exactly_one_source_row')
    for i, lit in enumerate(root['split_literals']):
        key='r'+str(i);new_node(work,ledger,key,[lit]);root['children'].append(key)
    write(work/'ledger.json', ledger)
    return ledger


def validate(work):
    """Reconstruct every node from the pinned parent and check coverage, not proofs."""
    ledger = read(work/'ledger.json');base=work/'parent'
    if ledger['schema'] != 1 or sha(base/'formula.cnf') != ledger['parent_sha256'] or sha(base/'export.json') != ledger['metadata_sha256'] or sha(base/'selectors.json') != ledger['selectors_sha256']:
        raise ValueError('parent/metadata corruption')
    for n,h in ledger['source_sha256'].items():
        if sha(HERE/n)!=h:raise ValueError('source changed; explicit migration required: '+n)
    rows=read(base/'selectors.json');variables={v for row in rows for a,v in row[4]}
    visited=set()
    def walk(key, assumptions):
        if key in visited:raise ValueError('duplicate or cyclic node')
        visited.add(key);node=ledger['nodes'][key]
        if node['assumptions']!=assumptions or read(work/'nodes'/key/'assumptions.json')!=assumptions:raise ValueError('assumptions mismatch')
        p=work/'nodes'/key/'formula.cnf'
        tmp=work/'verify-formula.tmp'
        try:
            formula(base,tmp,assumptions)
            if sha(tmp)!=node['cnf_sha256'] or sha(p)!=node['cnf_sha256']:raise ValueError('wrong child formula')
        finally:tmp.unlink(missing_ok=True)
        if node.get('probe_sha256') and sha(work/'nodes'/key/'probe.json')!=node['probe_sha256']:
            raise ValueError('probe record corruption')
        if node['children']:
            lits=node['split_literals']
            if node['status']!='SPLIT' or len(lits)!=len(node['children']):raise ValueError('invalid split')
            if key=='r':
                if node['split_kind']!='exactly_one_source_row' or lits!=[c['literal'] for c in plan(base)['cases']]:raise ValueError('incomplete initial coverage')
            elif node['split_kind']!='binary' or len(lits)!=2 or lits[0]!=-lits[1] or lits[0]<=0 or lits[0] not in variables or lits[0] in map(abs,assumptions):
                raise ValueError('incomplete binary coverage')
            for child,lit in zip(node['children'],lits):walk(child,assumptions+[lit])
        elif node['status'] not in ['PENDING','UNKNOWN','SAT_FINITE_CNF','CNF_UNSAT_RUP_VERIFIED']:
            raise ValueError('invalid leaf state')
        for attempt in node['attempts']:
            if attempt['files'].get('formula.cnf')!=node['cnf_sha256']:
                raise ValueError('proof/model attempt belongs to a different formula')
            for n,h in attempt['files'].items():
                if sha(work/'nodes'/key/attempt['directory']/n)!=h:raise ValueError('attempt artifact corruption')
        if node['status'] in ['SAT_FINITE_CNF','CNF_UNSAT_RUP_VERIFIED']:
            if not node['attempts'] or node['attempts'][-1]['status']!=node['status']:raise ValueError('unbacked status')
            attempt=node['attempts'][-1];cert=read(work/'nodes'/key/attempt['directory']/'certification.json')
            if cert['status']!=node['status'] or cert['cnf_sha256']!=node['cnf_sha256']:raise ValueError('wrong child certificate')
    walk('r',[])
    if visited!=set(ledger['nodes']):raise ValueError('unreachable ledger nodes')
    return ledger


def split_leaf(work, ledger, key, literal):
    node=ledger['nodes'][key]
    variables={v for row in read(work/'parent/selectors.json') for a,v in row[4]}
    if node['children'] or node['status']!='UNKNOWN' or literal not in variables or literal in map(abs,node['assumptions']):
        raise ValueError('invalid refinement')
    kids=[]
    # Atomic ledger commit publishes BOTH branches together. Orphans block safely.
    for i,lit in enumerate([literal,-literal]):
        child=key+str(i);new_node(work,ledger,child,node['assumptions']+[lit]);kids.append(child)
    node.update(status='SPLIT',children=kids,split_kind='binary',split_literals=[literal,-literal])
    write(work/'ledger.json',ledger)


def probe(folder, parent, limit):
    """Measure unit propagation for a deterministic mix of source/transit actions."""
    from pysat.solvers import Solver
    rows=read(parent/'selectors.json')
    groups=[[v for r in rows if (r[2]==-1)==source for a,v in r[4] if len(r[4])>1] for source in [True,False]]
    # Spread probes across each group instead of taking only the first vertex.
    candidates=[]
    for group in groups:
        if group:
            candidates.extend(group[min(len(group)-1,i*len(group)//max(1,limit//2))] for i in range(max(1,limit//2)))
    records=[]
    explicit=set(map(abs,read(folder/'assumptions.json')))
    with Solver(name='glucose3',bootstrap_with=(sorted(c) for c in iter_cnf(folder/'formula.cnf'))) as solver:
        ok,forced=solver.propagate();fixed=set(map(abs,forced))
        if not ok:return {'literal':None,'reason':'base propagation conflict; requires proof'}
        for v in sorted(set(candidates)-fixed-explicit):
            sides=[]
            for lit in [v,-v]:
                success,trail=solver.propagate(assumptions=[lit])
                sides.append({'consistent':success,'propagated':len(trail)})
            records.append({'literal':v,'sides':sides})
    # Balance the two propagated closures; score is heuristic, never a result.
    def score(r):
        a,b=[s['propagated'] for s in r['sides']]
        return (sum(not s['consistent'] for s in r['sides']),min(a,b),a+b,-r['literal'])
    unforced=[r for r in records if all(s['consistent'] for s in r['sides'])]
    best=max(unforced,key=score) if unforced else None
    return {'literal':best['literal'] if best else None,'records':records,'method':'bounded candidate unit-propagation scoring; not solver runtime prediction'}


def phase(folder, mode, seconds, parent=None):
    cmd=[sys.executable,str(HERE/'adaptive_cnf.py'),'worker','--work',str(folder),'--phase',mode]
    if parent:cmd+=['--parent',str(parent)]
    started=time.monotonic()
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed_out=False
    try:
        stdout,stderr=proc.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out=True
        os.killpg(proc.pid,signal.SIGKILL)  # only this owned process group
        stdout,stderr=proc.communicate()  # explicitly join the owned worker
    (folder/(mode+'.log')).write_bytes(stdout+stderr)
    return {'returncode':None if timed_out else proc.returncode,
            'seconds':time.monotonic()-started,'timeout':timed_out}


def run(work, seconds, node_seconds, probe_seconds, attempts, max_depth):
    deadline=time.monotonic()+seconds
    ledger=validate(work)
    used=0
    while used<attempts and time.monotonic()<deadline-1:
        leaves=[(k,n) for k,n in ledger['nodes'].items() if not n['children']]
        pending=sorted((k for k,n in leaves if n['status']=='PENDING'),key=lambda k:(len(k),k))
        if not pending:
            refine=sorted((k for k,n in leaves if n['status']=='UNKNOWN' and len(n['assumptions'])<max_depth and not n.get('probe_attempted')),key=lambda k:(len(k),k))
            if not refine:break
            key=refine[0];node=ledger['nodes'][key];folder=work/'nodes'/key
            p=phase(folder,'probe',min(probe_seconds,max(1,deadline-time.monotonic())),work/'parent')
            node['probe_attempted']=True;node['probe_run']=p
            if p['returncode']==0 and (folder/'probe.json').exists():
                report=read(folder/'probe.json');node['probe_sha256']=sha(folder/'probe.json')
                if report['literal'] is not None:
                    split_leaf(work,ledger,key,report['literal']);continue
            write(work/'ledger.json',ledger);continue
        key=pending[0];node=ledger['nodes'][key];folder=work/'nodes'/key
        trial=folder/('attempt-'+str(len(node['attempts'])))
        # Use a unique new directory; an interrupted uncommitted attempt is retained.
        while trial.exists():trial=folder/(trial.name+'-recovery')
        trial.mkdir();os.link(folder/'formula.cnf',trial/'formula.cnf')
        used+=1;cert={'status':'UNKNOWN','cnf_sha256':node['cnf_sha256']};phases={}
        phases['solve']=phase(trial,'solve',min(node_seconds,max(1,deadline-time.monotonic())))
        if phases['solve']['returncode']==0 and time.monotonic()<deadline-1:
            status=read(trial/'solver-status.json')['status']
            if status=='SAT_FINITE_CNF':
                shutil.copyfile(work/'parent/export.json',trial/'parent-export.json')
                shutil.copyfile(work/'parent/selectors.json',trial/'parent-selectors.json')
                write(trial/'split.json',{'child_sha256':node['cnf_sha256']})
                phases['decode']=phase(trial,'decode',min(node_seconds,max(1,deadline-time.monotonic())))
                if phases['decode']['returncode']==0:cert['status']='SAT_FINITE_CNF'
            elif status=='UNSAT_UNCERTIFIED':
                phases['check']=phase(trial,'check',min(node_seconds,max(1,deadline-time.monotonic())))
                if phases['check']['returncode']==0:cert=read(trial/'checked.json')
        cert['phases']=phases;write(trial/'certification.json',cert)
        record={'directory':trial.name,'status':cert['status'],'files':{p.name:sha(p) for p in trial.iterdir() if p.is_file()}}
        node['attempts'].append(record);node['status']=cert['status'];write(work/'ledger.json',ledger)
        print(json.dumps({'node':key,'status':node['status'],'attempts_this_run':used}),flush=True)
    leaves=[n for n in ledger['nodes'].values() if not n['children']]
    summary={'status':'UNKNOWN','scope':ledger['scope'],'leaves':len(leaves),'counts':{s:sum(n['status']==s for n in leaves) for s in ['PENDING','UNKNOWN','SAT_FINITE_CNF','CNF_UNSAT_RUP_VERIFIED']},'attempts_this_run':used,'note':'No parent/graph conclusion; audit rechecks closed leaves independently.'}
    write(work/'summary.json',summary);return summary


def audit(work):
    ledger=validate(work);closed=0;leaves=0
    for key,node in ledger['nodes'].items():
        if node['children']:continue
        leaves+=1
        if node['status']=='CNF_UNSAT_RUP_VERIFIED':
            folder=work/'nodes'/key/node['attempts'][-1]['directory']
            check(folder/'formula.cnf',folder/'proof.drup');closed+=1
    return {'checked_unsat_leaves':closed,'leaves':leaves,'finite_parent_unsat':closed==leaves,'scope':ledger['scope'],'graph_classification':'UNCHANGED'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['init','run','audit','validate','worker'])
    p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--parent',type=pathlib.Path)
    p.add_argument('--seconds',type=int,default=1200);p.add_argument('--node-seconds',type=int,default=120)
    p.add_argument('--probe-seconds',type=int,default=45);p.add_argument('--attempts',type=int,default=8)
    p.add_argument('--max-depth',type=int,default=3);p.add_argument('--phase',choices=['solve','check','decode','probe','audit'])
    a=p.parse_args();a.work=a.work.resolve()
    if a.mode=='worker':
        if a.phase=='solve':
            status=solve(a.work/'formula.cnf',a.work/'proof.drup')
            # Some backends return no proof for bootstrap unit contradictions.
            # Propose an empty clause; the independent checker MUST justify it.
            if status=='UNSAT_UNCERTIFIED' and not (a.work/'proof.drup').read_text().strip():
                (a.work/'proof.drup').write_text('0\n')
            write(a.work/'solver-status.json',{'status':status})
        elif a.phase=='check':write(a.work/'checked.json',check(a.work/'formula.cnf',a.work/'proof.drup'))
        elif a.phase=='decode':decode(a.work)
        elif a.phase=='probe':write(a.work/'probe.json',probe(a.work,a.parent,16))
        elif a.phase=='audit':write(a.work/'audit.json',audit(a.work))
        else:p.error('worker requires phase')
        return
    if a.mode=='init':
        if a.parent is None:p.error('init requires parent')
        initialize(a.parent,a.work);return
    with (a.work/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.mode=='run':
            if not (1<=a.seconds<=3600 and 1<=a.node_seconds<=600 and 1<=a.probe_seconds<=120 and 1<=a.attempts<=32 and 1<=a.max_depth<=8):p.error('budget outside allowed range')
            print(json.dumps(run(a.work,a.seconds,a.node_seconds,a.probe_seconds,a.attempts,a.max_depth)))
        elif a.mode=='audit':
            if not 1<=a.seconds<=3600:p.error('audit budget must be 1..3600 seconds')
            (a.work/'audit.json').unlink(missing_ok=True)
            result=phase(a.work,'audit',a.seconds)
            if result['returncode']!=0:
                print(json.dumps({'status':'UNKNOWN','audit_run':result}));sys.exit(1)
            print(json.dumps(read(a.work/'audit.json')))
        else:validate(a.work);print('coverage/hash validation passed; no proof replay')


if __name__=='__main__':main()
