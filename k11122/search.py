"""Unrestricted finite-domain synthesis; exhaustive residual verification."""
import argparse, hashlib, itertools, json, os, pathlib, subprocess, time
import z3

def graph(n):
    return [(u,v) for u in range(n) for v in range(u+1,n)
            if n != 7 or (u,v) not in [(3,4),(5,6)]]

def adjacency(n, edges, mask):
    a=[0]*n
    for i,(u,v) in enumerate(edges):
        if mask>>i&1: a[u]|=1<<v; a[v]|=1<<u
    return a

def vertices(mask,n): return [v for v in range(n) if mask>>v&1]

class Encoding:
    def __init__(self,n,t):
        self.n,self.t,self.edges=n,t,graph(n)
        self.s=z3.Solver(); self.rows={}; self.masks=[]
        host=adjacency(n,self.edges,(1<<len(self.edges))-1)
        for u in range(n):
            if u==t: continue
            for L in range(1,1<<n):
                if L & ~host[u]: continue
                for p,b in [(-1,0)]+[(p,b) for p in vertices(L,n) for b in range(2)]:
                    key=(u,L,p,b); x=z3.Int('a_'+'_'.join(map(str,key)))
                    self.rows[key]=x
                    # Safe immediate delivery is the ONLY normalization.
                    domain=[2*t] if L>>t&1 else [2*v+h for v in vertices(L,n) for h in range(2)]
                    self.s.add(z3.Or([x==v for v in domain]))
    def add(self,mask):
        if mask in self.masks: return
        self.masks.append(mask); n,t=self.n,self.t
        a=adjacency(n,self.edges,mask)
        C={t}; todo=[t]
        while todo:
            for v in vertices(a[todo.pop()],n):
                if v not in C: C.add(v); todo.append(v)
        keys=[(u,p,b) for u in C if u!=t for p in vertices(a[u],n) for b in range(2)]
        ranks={k:z3.Int('r_'+str(mask)+'_'+'_'.join(map(str,k))) for k in keys}
        for r in ranks.values(): self.s.add(r>=0,r<=len(keys))
        def good(u,x,upper=None):
            terms=[]
            for v in vertices(a[u],n):
                for h in range(2):
                    if v==t: cond=z3.BoolVal(True)
                    else:
                        r=ranks[(v,u,h)]
                        cond=r>0 if upper is None else z3.And(r>0,r<upper)
                    terms.append(z3.And(x==2*v+h,cond))
            return z3.Or(terms)
        for (u,p,b),r in ranks.items():
            self.s.add(z3.Implies(r>0,good(u,self.rows[u,a[u],p,b],r)))
        for u in C-{t}: self.s.add(good(u,self.rows[u,a[u],-1,0]))
    def policy(self):
        m=self.s.model()
        return {k:m.eval(x).as_long() for k,x in self.rows.items()}

def write_policy(path,n,t,rows):
    path.write_text(f'{n} {t}\n'+''.join(' '.join(map(str,(*k,v)))+'\n' for k,v in sorted(rows.items())))

def partition(enc, branch):
    """Disjoint exhaustive split by physical first hop, never a WLOG claim."""
    if branch == -1: return None
    host=adjacency(enc.n,enc.edges,(1<<len(enc.edges))-1)
    u=next(u for u in range(enc.n) if u!=enc.t and
           len(vertices(host[u] & ~(1<<enc.t),enc.n))>=2)
    neighbors=vertices(host[u] & ~(1<<enc.t),enc.n)[:2]
    L=sum(1<<v for v in neighbors); key=(u,L,-1,0)
    enc.s.add(z3.Or(enc.rows[key]==2*neighbors[branch],
                    enc.rows[key]==2*neighbors[branch]+1))
    return {'row':list(key),'neighbors':neighbors,'branch':branch}

def retry_parameters(base, attempt, remaining):
    return max(1,int(min(base*2**min(attempt,4),600,remaining)*1000)), 20261031+attempt

def load_checkpoint(path,target):
    old=json.loads(path.read_text())
    if old.get('target')!=target or old.get('schema') not in (1,2):
        raise ValueError('checkpoint mismatch')
    masks=old['masks']
    if not masks or any(type(m)!=int or not 0<=m<1<<19 for m in masks):
        raise ValueError('invalid checkpoint masks')
    # Only unconditional residual obligations are imported, NEVER a branch
    # status, candidate, or restricted learned assertion.
    return list(dict.fromkeys(masks))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--target',type=int,choices=[0,3],required=True)
    p.add_argument('--seconds',type=int,default=1200); p.add_argument('--solve-seconds',type=int,default=60)
    p.add_argument('--branch',type=int,choices=[-1,0,1],default=-1)
    p.add_argument('--output',type=pathlib.Path,required=True); p.add_argument('--resume',type=pathlib.Path)
    args=p.parse_args()
    if not 1<=args.seconds<=14400 or not 1<=args.solve_seconds<=600: p.error('budget out of range')
    out=args.output
    if out.exists() and any(out.iterdir()): p.error('output must be empty; use --resume with a NEW output')
    out.mkdir(parents=True,exist_ok=True); start=time.monotonic(); deadline=start+args.seconds
    binary=out/'verify'; subprocess.run(['g++','-O3','-std=c++17',str(pathlib.Path(__file__).with_name('verify.cpp')),'-o',str(binary)],check=True)
    enc=Encoding(7,args.target); split=partition(enc,args.branch)
    masks=[(1<<19)-1]+[((1<<19)-1)^(1<<i) for i in range(19)]
    if args.resume: masks=load_checkpoint(args.resume,args.target)
    initial_count=len(masks)
    status='UNKNOWN'; iteration=0; retries=0; reason=''; last_candidate=None
    def checkpoint():
        data={'schema':2,'target':args.target,'masks':enc.masks,'status':status,'iteration':iteration,
              'partition':split,'initial_residuals':initial_count,'consecutive_unknowns':retries,
              'reason':reason,'last_candidate':last_candidate,
              'elapsed_seconds':time.monotonic()-start,'z3':z3.get_version_string(),
              'commit':os.environ.get('GITHUB_SHA'),'model':'static-undirected/common-source-local/two-state',
              'resume_sha256':hashlib.sha256(args.resume.read_bytes()).hexdigest() if args.resume else None}
        tmp=out/'checkpoint.tmp'; tmp.write_text(json.dumps(data,indent=2)); tmp.replace(out/'checkpoint.json')
    # Preserve the COMPLETE imported mask list before potentially expensive rebuild.
    enc.masks=list(masks); checkpoint(); enc.masks=[]
    for mask in masks: enc.add(mask)
    checkpoint()
    while time.monotonic()<deadline:
        timeout,seed=retry_parameters(args.solve_seconds,retries,deadline-time.monotonic())
        enc.s.set(timeout=timeout,random_seed=seed)
        result=enc.s.check(); iteration+=1
        reason=enc.s.reason_unknown() if result==z3.unknown else ''
        record={'iteration':iteration,'residuals':len(enc.masks),'solver':str(result),
                'timeout_ms':timeout,'seed':seed,'reason':reason,'elapsed_seconds':time.monotonic()-start}
        with (out/'progress.jsonl').open('a') as f: f.write(json.dumps(record)+'\n')
        print(json.dumps(record),flush=True)
        if result==z3.unknown:
            retries+=1; checkpoint()
            if reason not in ('timeout','canceled','resource limits','max. resource limit exceeded'):
                break
            continue
        if result==z3.unsat:
            status='UNSAT_UNCERTIFIED'; checkpoint(); break
        retries=0
        rows=enc.policy(); write_policy(out/'candidate.tsv',7,args.target,rows)
        replay=subprocess.run([str(binary),str(out/'candidate.tsv')],check=True,capture_output=True,text=True,timeout=120)
        audit=json.loads(replay.stdout); (out/'verification.json').write_text(json.dumps(audit,indent=2))
        expected=2979236 if args.target==0 else 2937186
        if audit['masks']!=524288 or audit['obligations']!=expected: raise RuntimeError('incomplete verification')
        last_candidate={'iteration':iteration,'sha256':hashlib.sha256((out/'candidate.tsv').read_bytes()).hexdigest(),
                        'failures':audit['failures']}
        if not audit['failures']:
            status='VERIFIED_POSITIVE'; checkpoint(); break
        if not audit['counterexamples'] or any(m in enc.masks for m in audit['counterexamples']):
            raise RuntimeError('encoder/checker disagreement: candidate fails enforced residual')
        for mask in audit['counterexamples']: enc.add(mask)
        checkpoint()
    checkpoint()
    (out/'last.smt2').write_text(enc.s.to_smt2())
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='SHA256.json'}
    (out/'SHA256.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps({'status':status,'iterations':iteration,'residuals':len(enc.masks),'partition':split}),flush=True)
if __name__=='__main__': main()
