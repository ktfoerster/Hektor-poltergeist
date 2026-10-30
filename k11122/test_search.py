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
if __name__=='__main__':unittest.main()
