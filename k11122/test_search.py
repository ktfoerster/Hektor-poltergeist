import itertools,json,pathlib,subprocess,tempfile,unittest
import z3
from search import Encoding,write_policy,graph
class Tests(unittest.TestCase):
 def test_small_complete_and_corruption(self):
  for n in (2,3,4):
   e=Encoding(n,0)
   for mask in range(1<<len(graph(n))):e.add(mask)
   self.assertEqual(e.s.check(),z3.sat)
   with tempfile.TemporaryDirectory() as d:
    d=pathlib.Path(d);write_policy(d/'p',n,0,e.policy())
    subprocess.run(['g++','-O2','-std=c++17',str(pathlib.Path(__file__).with_name('verify.cpp')),'-o',str(d/'v')],check=True)
    r=subprocess.run([str(d/'v'),str(d/'p')],check=True,capture_output=True,text=True)
    self.assertEqual(json.loads(r.stdout)['failures'],0)
    (d/'p').write_text((d/'p').read_text()+'1 1 -1 0 999\n')
    self.assertNotEqual(subprocess.run([str(d/'v'),str(d/'p')],capture_output=True).returncode,0)
 def test_common_source_and_no_arbitrary_arrival(self):
  e=Encoding(3,0);e.add(7);e.add(3)
  self.assertEqual(len([k for k in e.rows if k==(1,5,-1,0)]),1)
  self.assertEqual(e.s.check(),z3.sat)
 def test_encoding_against_all_two_vertex_policies(self):
  # Two live directed ports, either emitted bit, each source/transit row.
  e=Encoding(2,0);e.add(1)
  keys=list(e.rows)
  for values in itertools.product((0,1),repeat=len(keys)):
   e.s.push()
   # Normalized direct delivery fixes bit zero; physical outcome is independent.
   for k,v in zip(keys,values):e.s.add(e.rows[k]==v)
   self.assertEqual(e.s.check(),z3.sat if all(v==0 for v in values) else z3.unsat)
   e.s.pop()


class SemanticTests(unittest.TestCase):
 def test_transient_source_revisit_and_unreachable_cycle(self):
  e=Encoding(4,0);e.add(57) # 01,12,13,23
  assignments={(3,6,-1,0):2,
               (3,6,2,0):5,(2,10,3,1):2,
               (2,10,3,0):7,(3,6,2,1):4}
  for k,v in assignments.items():e.s.add(e.rows[k]==v)
  e.s.push();e.s.add(e.rows[2,10,-1,0]==6)
  self.assertEqual(e.s.check(),z3.sat);e.s.pop()
  # Source 2 goes 2->3->2->1->0; a different arrival/bit is trapped.
  e.s.add(e.rows[2,10,-1,0]==7)
  self.assertEqual(e.s.check(),z3.unsat)
 def test_exhaustive_triangle_policies_against_literal_walks(self):
  from search import adjacency,vertices
  e=Encoding(3,0)
  for mask in range(8):e.add(mask)
  free=[k for k in e.rows if not k[1]&1]
  for bits in itertools.product(range(2),repeat=len(free)):
   rows={k:0 for k in e.rows}
   for k,h in zip(free,bits):rows[k]=2*vertices(k[1],3)[0]+h
   expected=True
   for mask in range(8):
    a=adjacency(3,graph(3),mask); C={0}
    for _ in range(3):C|={v for u in list(C) for v in vertices(a[u],3)}
    for src in C-{0}:
     u,p,b=src,-1,0;seen=set()
     while u!=0 and (u,p,b) not in seen:
      seen.add((u,p,b));v=rows[u,a[u],p,b];u,p,b=v//2,u,v%2
     expected &= u==0
   e.s.push()
   for k,v in rows.items():e.s.add(e.rows[k]==v)
   self.assertEqual(e.s.check()==z3.sat,expected)
   e.s.pop()
 def test_partition_coverage_disjoint_and_resume(self):
  from search import partition,load_checkpoint,retry_parameters
  e=Encoding(7,0); spec=partition(e,0); key=tuple(spec['row'])
  a,b=spec['neighbors'];x=z3.Int('split_test')
  s=z3.Solver();domain=z3.Or(*[x==2*v+h for v in [a,b] for h in [0,1]])
  left=z3.Or(x==2*a,x==2*a+1);right=z3.Or(x==2*b,x==2*b+1)
  s.add(domain,z3.Not(z3.Or(left,right)));self.assertEqual(s.check(),z3.unsat)
  s=z3.Solver();s.add(left,right);self.assertEqual(s.check(),z3.unsat)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'c.json';p.write_text(json.dumps({'schema':1,'target':0,'masks':[1,2,1]}))
   self.assertEqual(load_checkpoint(p,0),[1,2])
   with self.assertRaises(ValueError):load_checkpoint(p,3)
  self.assertEqual(retry_parameters(60,0,1200)[0],60000)
  self.assertEqual(retry_parameters(60,1,1200)[0],120000)
  self.assertEqual(retry_parameters(60,5,17)[0],17000)

if __name__=='__main__':unittest.main()
