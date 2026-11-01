import copy
import json
import pathlib
import tempfile
import unittest
from pysat.solvers import Solver
from proof_cnf import export, iter_cnf, sha
from adaptive_cnf import initialize, validate, split_leaf, write, read, run, audit


class AdaptiveTests(unittest.TestCase):
    def setup_instance(self, temp):
        base=pathlib.Path(temp);parent=base/'parent';work=base/'work'
        export(parent,0,[0,1,63],n=4)
        ledger=initialize(parent,work)
        return parent,work,ledger

    def test_recursive_coverage_resume_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,work,ledger=self.setup_instance(temp)
            # Mark a simulated budget exhaustion; it carries no proof status.
            ledger['nodes']['r0']['status']='UNKNOWN'
            rows=read(parent/'selectors.json')
            var=next(v for r in rows for a,v in r[4] if v!=ledger['nodes']['r0']['assumptions'][0])
            # An interrupted split directory is preserved, not trusted.
            orphan=work/'nodes/r00';orphan.mkdir();(orphan/'partial').write_text('interrupted')
            split_leaf(work,ledger,'r0',var)
            validate(work)
            self.assertTrue(list((work/'orphans').rglob('partial')))
            nodes=ledger['nodes'];leaves=[n for n in nodes.values() if not n['children']]
            self.assertEqual(len(leaves),5)
            with Solver(name='glucose3',bootstrap_with=(list(c) for c in iter_cnf(parent/'formula.cnf'))) as solver:
                # Block every leaf cube: no satisfying parent assignment remains.
                for n in leaves:solver.add_clause([-v for v in n['assumptions']])
                self.assertFalse(solver.solve())
            for i,a in enumerate(leaves):
                for b in leaves[i+1:]:
                    with Solver(name='glucose3',bootstrap_with=(list(c) for c in iter_cnf(parent/'formula.cnf'))) as solver:
                        self.assertFalse(solver.solve(assumptions=a['assumptions']+b['assumptions']))
            bad=copy.deepcopy(ledger);bad['nodes']['r0']['split_literals']=[var,var]
            write(work/'ledger.json',bad)
            with self.assertRaises(ValueError):validate(work)
            write(work/'ledger.json',ledger)
            f=work/'nodes/r00/formula.cnf';old=f.read_bytes();f.write_bytes(old+b'1 0\n')
            with self.assertRaises(ValueError):validate(work)
            f.write_bytes(old)
            # Resume uses the published ledger, never reconstructs lost sibling coverage.
            self.assertEqual(validate(work),ledger)
            s=run(work,30,10,5,1,3)
            self.assertEqual(s['attempts_this_run'],1)
            validate(work)
            s=run(work,30,10,5,1,3)
            self.assertEqual(s['attempts_this_run'],1)
            validate(work)

    def test_wrong_child_proof_and_stale_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,work,ledger=self.setup_instance(temp)
            key='r0';n=ledger['nodes'][key];trial=work/'nodes'/key/'attempt-fake';trial.mkdir()
            # An empty-clause proof belongs to an inconsistent formula, not this SAT child.
            (trial/'formula.cnf').write_bytes((work/'nodes'/key/'formula.cnf').read_bytes())
            (trial/'proof.drup').write_text('0\n')
            write(trial/'certification.json',{'status':'CNF_UNSAT_RUP_VERIFIED','cnf_sha256':n['cnf_sha256']})
            n['status']='CNF_UNSAT_RUP_VERIFIED';n['attempts']=[{'directory':trial.name,'status':n['status'],'files':{p.name:sha(p) for p in trial.iterdir()}}]
            write(work/'ledger.json',ledger)
            with self.assertRaises(ValueError):audit(work)
            (work/'parent/selectors.json').write_text('[]')
            with self.assertRaises(ValueError):validate(work)

    def test_real_sat_replay_and_no_parent_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,work,ledger=self.setup_instance(temp)
            result=run(work,60,15,5,4,2)
            self.assertEqual(result['counts']['SAT_FINITE_CNF'],4)
            self.assertFalse(audit(work)['finite_parent_unsat'])
            ledger=validate(work)
            for key in ['r0','r1','r2','r3']:
                n=ledger['nodes'][key];folder=work/'nodes'/key/n['attempts'][-1]['directory']
                self.assertEqual(read(folder/'routing-replay.json')['status'],'FINITE_SAT_GLOBALLY_INVALID')
                # A status without the corresponding exact-child certification is rejected.
            n=ledger['nodes']['r0'];n['status']='CNF_UNSAT_RUP_VERIFIED'
            write(work/'ledger.json',ledger)
            with self.assertRaises(ValueError):validate(work)

    def test_checked_unsat_aggregation_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            base=pathlib.Path(temp);parent=base/'parent';work=base/'work'
            export(parent,0,[0,1,63],n=4)
            # Deliberately inconsistent Boolean fixture, never a routing claim.
            f=parent/'formula.cnf';lines=f.read_text().splitlines()
            h=lines[0].split();h[3]=str(int(h[3])+2)
            f.write_text(' '.join(h)+'\n'+'\n'.join(lines[1:])+'\n1 0\n-1 0\n')
            meta=read(parent/'export.json');meta['clauses']+=2;meta['cnf_sha256']=sha(f)
            write(parent/'export.json',meta)
            initialize(parent,work)
            result=run(work,60,15,5,4,2)
            self.assertEqual(result['counts']['CNF_UNSAT_RUP_VERIFIED'],4)
            self.assertTrue(audit(work)['finite_parent_unsat'])
            ledger=read(work/'ledger.json');ledger['nodes']['r']['children'].pop()
            write(work/'ledger.json',ledger)
            with self.assertRaises(ValueError):validate(work)

    def test_probe_excludes_explicit_decisions(self):
        from adaptive_cnf import probe
        with tempfile.TemporaryDirectory() as temp:
            parent,work,ledger=self.setup_instance(temp)
            result=probe(work/'nodes/r0',work/'parent',16)
            if result['literal'] is not None:
                self.assertNotIn(result['literal'],map(abs,ledger['nodes']['r0']['assumptions']))
            self.assertNotIn('status',result)  # heuristic observations certify nothing

    def test_driver_refines_unknown_leaves(self):
        with tempfile.TemporaryDirectory() as temp:
            parent,work,ledger=self.setup_instance(temp)
            for key,node in ledger['nodes'].items():
                if not node['children']:node['status']='UNKNOWN'
            write(work/'ledger.json',ledger)
            result=run(work,60,15,10,2,3)
            current=validate(work)
            self.assertGreater(len(current['nodes']),5)
            self.assertEqual(result['attempts_this_run'],2)
            self.assertFalse(audit(work)['finite_parent_unsat'])

if __name__=='__main__':unittest.main()
