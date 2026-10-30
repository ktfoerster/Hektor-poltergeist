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

def main():
    p=argparse.ArgumentParser(); p.add_argument('--target',type=int,choices=[0,3],required=True)
    p.add_argument('--seconds',type=int,default=1200); p.add_argument('--solve-seconds',type=int,default=60)
    p.add_argument('--output',type=pathlib.Path,required=True); p.add_argument('--resume',type=pathlib.Path)
    args=p.parse_args()
    if not 1<=args.seconds<=14400 or not 1<=args.solve_seconds<=600: p.error('budget out of range')
    out=args.output; out.mkdir(parents=True,exist_ok=True); start=time.monotonic(); deadline=start+args.seconds
    binary=out/'verify'; subprocess.run(['g++','-O3','-std=c++17',str(pathlib.Path(__file__).with_name('verify.cpp')),'-o',str(binary)],check=True)
    enc=Encoding(7,args.target)
    masks=[(1<<19)-1]+[((1<<19)-1)^(1<<i) for i in range(19)]
    if args.resume:
        old=json.loads(args.resume.read_text())
        if old['target']!=args.target or old['schema']!=1: raise ValueError('checkpoint mismatch')
        masks=old['masks']
    for mask in masks:
        if not 0<=mask<1<<19: raise ValueError('bad residual')
        enc.add(mask)
    status='UNKNOWN'; iteration=0
    def checkpoint():
        data={'schema':1,'target':args.target,'masks':enc.masks,'status':status,'iteration':iteration,
              'elapsed_seconds':time.monotonic()-start,'z3':z3.get_version_string(),
              'commit':os.environ.get('GITHUB_SHA'),'model':'static-undirected/common-source-local/two-state'}
        tmp=out/'checkpoint.tmp'; tmp.write_text(json.dumps(data,indent=2)); tmp.replace(out/'checkpoint.json')
    checkpoint()
    while time.monotonic()<deadline:
        enc.s.set(timeout=max(1,int(min(args.solve_seconds,deadline-time.monotonic())*1000)))
        result=enc.s.check(); iteration+=1
        with (out/'progress.jsonl').open('a') as f: f.write(json.dumps({'iteration':iteration,'residuals':len(enc.masks),'solver':str(result)})+'\n')
        if result!=z3.sat:
            status='UNSAT_UNCERTIFIED' if result==z3.unsat else 'UNKNOWN'
            (out/'solver.txt').write_text(str(result)+'\n'+enc.s.reason_unknown())
            (out/'last.smt2').write_text(enc.s.to_smt2()); checkpoint(); break
        rows=enc.policy(); write_policy(out/'candidate.tsv',7,args.target,rows)
        replay=subprocess.run([str(binary),str(out/'candidate.tsv')],check=True,capture_output=True,text=True,timeout=120)
        audit=json.loads(replay.stdout); (out/'verification.json').write_text(json.dumps(audit,indent=2))
        if not audit['failures']:
            status='VERIFIED_POSITIVE'; checkpoint(); break
        for mask in audit['counterexamples']: enc.add(mask)
        checkpoint()
    checkpoint()
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='SHA256.json'}
    (out/'SHA256.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps({'status':status,'iterations':iteration,'residuals':len(enc.masks)}))
if __name__=='__main__': main()
