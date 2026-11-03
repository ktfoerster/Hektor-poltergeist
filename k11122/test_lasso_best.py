"""Independent cross-language quality tests and best-policy integrity checks."""
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from lasso_best import BestObserved, independently_check_best, independent_quality
from lasso_witness import audit, selector_rows


@unittest.skipUnless(shutil.which("g++"), "g++ required")
class BestQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / "lasso_quality"
        cls.scanner = Path(cls.temp.name) / "lasso_batch"
        src = Path(__file__).with_name("lasso_quality.cpp")
        subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                        str(src), "-o", str(cls.binary)],
                       check=True, timeout=35, capture_output=True)
        subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                        str(src.with_name("lasso_batch.cpp")), "-o", str(cls.scanner)],
                       check=True, timeout=35, capture_output=True)

    def _write(self, root, n, target, masks, policy):
        root.mkdir()
        (root / "masks.json").write_text(json.dumps(masks) + "\n")
        (root / "masks.txt").write_text("".join(f"{m}\n" for m in masks))
        filename = root / "last-policy.tsv"
        filename.write_text(f"{n} {target}\n" + "".join(
            " ".join(map(str, (*key, value))) + "\n"
            for key, value in sorted(policy.items())))
        return filename

    def test_routing_quality_exact_against_independent_python(self):
        randomizer = random.Random(20261103)
        for n, target in ((3, 2), (4, 3), (7, 0), (7, 3)):
            edge_count=n*(n-1)//2-(2 if n==7 else 0)
            for trial in range(5):
                masks=sorted(randomizer.sample(range(1<<edge_count),
                            min(65,1<<edge_count)))
                rows=selector_rows(n,target)
                policy={key:randomizer.choice(choices)[0] for key,choices in rows.items()}
                with tempfile.TemporaryDirectory() as t:
                    root=Path(t)/"case"
                    filename=self._write(root,n,target,masks,policy)
                    proc=subprocess.run([str(self.binary),str(filename),
                                         str(root/"masks.txt")],
                                        capture_output=True,text=True,check=True,timeout=10)
                    parsed=json.loads(proc.stdout)
                    independent=independent_quality(filename,n,target,masks)
                    for key,value in independent.items():
                        self.assertEqual(parsed[key],value,(n,target,trial,key))
                    self.assertEqual(parsed["schema"],1)

    def test_best_scored_policy_ordering_and_tamper_detection(self):
        rng=random.Random(20261103)
        n,target=4,3
        rows=selector_rows(n,target)
        masks=[7,19,35,41]
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"experiment"
            root.mkdir()
            (root/"masks.json").write_text(json.dumps(masks)+"\n")
            (root/"masks.txt").write_text("".join(f"{m}\n" for m in masks))
            observer=BestObserved(root,n,target,-1,masks,self.binary,interval=1)
            rank_list=[]
            import hashlib
            for idx in range(1,37):
                policy={key:rng.choice(choices)[0] for key,choices in rows.items()}
                path=root/"last-policy.tsv"
                path.write_text(f"{n} {target}\n"+"".join(
                    " ".join(map(str,(*key,value)))+"\n"
                    for key,value in sorted(policy.items())))
                q=independent_quality(path,n,target,masks)
                rank_list.append((q["failing_residual_masks"],q["failed_connected_sources"],
                                  hashlib.sha256(path.read_bytes()).hexdigest()))
                observer.consider(path,idx)
            self.assertEqual(observer.scored,36)
            verified=independently_check_best(root)
            self.assertEqual(verified["status"],"INDEPENDENTLY_REPLAYED_HISTORICAL_BEST")
            self.assertEqual(verified["source_model_index"],
                             observer.best["source_model_index"])
            self.assertEqual(min(rank_list),observer.best_rank)
            original=(root/"best-policy.tsv").read_bytes()
            (root/"best-policy.tsv").write_bytes(original+b"\n")
            with self.assertRaises(ValueError):
                independently_check_best(root)
            (root/"best-policy.tsv").write_bytes(original)
            self.assertEqual(independently_check_best(root)["quality"],observer.best["quality"])
            (root/"masks.json").write_text("[19]\n")
            with self.assertRaises(ValueError):
                independently_check_best(root)

    def test_best_sampled_deterministic_interval_and_bad_binary(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"p"
            rows=selector_rows(4,3)
            policy={key:values[0][0] for key,values in rows.items()}
            path=self._write(root,4,3,[41],policy)
            tracker=BestObserved(root,4,3,-1,[41],self.binary,interval=4)
            for i in range(1,13):
                tracker.consider(path,i)
            self.assertEqual(tracker.scored,4)
            self.assertEqual(len((root/"quality-samples.jsonl").read_text().splitlines()),4)
            for invalid in (0, True, 1025, 1.2, "4"):
                with self.assertRaises(ValueError):
                    BestObserved(root,4,3,-1,[41],self.binary,interval=invalid)
            for bad in ("not-a-real-policy", "wrong-number"):
                proc=subprocess.run([str(self.binary),bad,str(root/"masks.txt")],
                                    capture_output=True,text=True)
                self.assertNotEqual(proc.returncode,0)

    def test_live_journal_and_generation_accounting(self):
        try:
            from lasso_search import run
        except ModuleNotFoundError:
            self.skipTest("pinned python-sat unavailable")
        for checkpoint_mode in ("journal","generations"):
            with tempfile.TemporaryDirectory() as t:
                root=Path(t)
                output=root/"result"
                stats=run(output,4,3,-1,[41],1.5,
                          walker="cpp",batch_binary=self.scanner,
                          best_interval=1,quality_binary=self.binary,
                          checkpoint_mode=checkpoint_mode,checkpoint_seconds=0.3)
                self.assertEqual(stats["quality_tracking_interval"],1)
                self.assertEqual(stats["quality_scored_raw_models"],stats["raw_models"])
                self.assertGreaterEqual(stats["quality_improvements"],1)
                self.assertEqual(audit(output)["status"],"CHECKED")
                verified=independently_check_best(output)
                self.assertEqual(verified["quality"],stats["best_observed_raw_quality"])
                self.assertEqual(stats["best_policy_independent_status"],
                                 "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST")
                with self.assertRaises(ValueError):
                    run(root/"invalid",4,3,-1,[41],1,
                        walker="python",best_interval=1,quality_binary=self.binary)
                self.assertFalse((root/"invalid").exists())


if __name__=="__main__":
    unittest.main()
