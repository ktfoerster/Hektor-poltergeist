"""Independent tests of nonportable, same-process certified transfer caching."""
import json
from pathlib import Path
import tempfile
import unittest

from lasso_transfer import transfer
from lasso_transfer_session import certify_session, SessionTransfer
from lasso_witness import audit
from test_lasso_transfer import fixture


class AttestedSessionTests(unittest.TestCase):
    def test_same_witnesses_as_independent_uncached_transfer(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            fixture(src)
            cached = certify_session(src, 4, 3, 1, [19, 35])
            self.assertEqual(cached.certification["transferred"], 1)
            self.assertEqual(cached.certification["branch_vacuous"], 1)
            self.assertEqual(cached.certification["source_witnesses"], 2)
            uncached_clauses, uncached_items = [], []
            info = transfer(src, 4, 3, 1, [19, 35],
                            uncached_clauses.append, uncached_items.append)
            self.assertEqual(cached.certification, info)
            for _ in range(3):
                clauses, items = [], []
                reuse = cached.emit(4, 3, 1, [19, 35],
                                    clauses.append, items.append)
                self.assertEqual(clauses, uncached_clauses)
                self.assertEqual(items, uncached_items)
                self.assertEqual(reuse["transferred"], info["transferred"])
                self.assertEqual(reuse["cache_semantic_audits_this_import"], 0)
                self.assertFalse(reuse["cache_is_portable_proof"])
                self.assertEqual(reuse["source_audit"], info["source_audit"])

    def test_tampering_cross_target_cross_branch_and_forgery_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            fixture(src)
            cached = certify_session(src, 4, 3, 1, [19, 35])
            seen = []
            for n,target,branch,masks in [
                    (4,3,0,[19,35]), (4,0,1,[19,35]),
                    (7,3,1,[19,35]), (4,3,1,[19]),
                    (4,3,1,[35,19])]:
                with self.assertRaises(ValueError):
                    cached.emit(n,target,branch,masks, seen.append, seen.append)
                self.assertEqual(seen, [])
            fake = SessionTransfer(
                cached.source_path, cached.n, cached.target,
                cached.destination_branch, cached.masks, cached.entries,
                cached.attested_source_hashes, cached.certification, object())
            with self.assertRaises(ValueError):
                fake.emit(4,3,1,[19,35],seen.append,seen.append)
            self.assertEqual(seen, [])
            with self.assertRaises(ValueError):
                cached.emit(4,3,1,[19,35],seen.append,seen.append,
                            expected_source_hashes={"changed":"sha"})
            # Once certified, the cache does not trust edited source files:
            path = src / "witnesses.jsonl"
            path.write_text(path.read_text() + "\n")
            with self.assertRaises(ValueError):
                cached.emit(4,3,1,[19,35],seen.append,seen.append)
            self.assertEqual(seen, [])

    def test_bad_source_rejected_during_creation_and_source_file_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source"
            fixture(src)
            path = src / "formula.cnf"
            path.write_text(path.read_text().replace(" 0\n", " 99\n", 1))
            with self.assertRaises(ValueError):
                certify_session(src, 4,3,1,[19,35])
            self.assertEqual(src.parent.glob("*.cnf").__class__.__name__,
                             "generator")  # no output manufactured

    def test_both_checkpoint_modes_import_and_recheck_destination(self):
        try:
            from lasso_search import run
        except ModuleNotFoundError:
            self.skipTest("requires pinned python-sat")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root / "source")
            cached=certify_session(root / "source",4,3,1,[19,35])
            for mode in ("journal","generations"):
                dst=root / mode
                result=run(dst,4,3,1,[19,35],1.4,
                           transfer_session_cache=cached,
                           allow_audited_migration=True,
                           budget_scope="search",
                           checkpoint_mode=mode,checkpoint_seconds=0.3)
                self.assertEqual(result["inherited_witnesses"],1)
                self.assertEqual(result["transfer_clauses"],1)
                self.assertEqual(audit(dst)["status"],"CHECKED")
                manifest=json.loads((dst / ("current/manifest.json" if mode=="generations"
                                            else "manifest.json")).read_text())
                m=manifest["imported"]["opposite_branch_certificates"]
                self.assertEqual(m["cache_mode"],"same_process_fully_audited_then_reused")
                self.assertEqual(m["cache_semantic_audits_this_import"],0)
            with self.assertRaises(ValueError):
                run(root/"invalid",4,3,1,[19,35],1,
                    transfer_session_cache=cached,
                    transfer_opposite_bundle=root/"source")
            self.assertFalse((root/"invalid").exists())
            with self.assertRaises(ValueError):
                run(root/"notcached",4,3,1,[19,35],1,
                    transfer_session_cache={"fake":"cache"})
            self.assertFalse((root/"notcached").exists())


if __name__ == "__main__":
    unittest.main()
