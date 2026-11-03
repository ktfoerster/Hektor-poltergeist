"""Deterministic hybrid selection, audited resume and real SAT integration."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from lasso_selection_schedule import (
    validate_selection, effective_selection, inherited_model_offset
)


class ScheduleTests(unittest.TestCase):
    def test_exact_periodic_schedule_and_no_policy_restriction(self):
        for period in (2, 4, 8, 17, 1024):
            for index in range(1, 2 * period + 1):
                mode = effective_selection("hybrid", period, index)
                expected = "short-diverse" if index % period == 0 else "first"
                self.assertEqual(mode, expected)
                self.assertEqual(effective_selection("first", period, index), "first")
                self.assertEqual(effective_selection("short-diverse", period, index),
                                 "short-diverse")
        # Decision scheduling must not alter selector variables/clauses.
        from sat_search import BooleanEncoding, partition
        for n, target in ((4, 3), (7, 0), (7, 3)):
            enc = BooleanEncoding(n, target)
            try:
                partition(enc, 0)
                before = (enc.top, enc.clause_count, enc.fingerprint.hexdigest())
                for k in range(1, 41):
                    effective_selection("hybrid", 8, k)
                self.assertEqual((enc.top, enc.clause_count, enc.fingerprint.hexdigest()),
                                 before)
            finally:
                enc.delete()

    def test_reject_non_cpp_and_invalid_intervals(self):
        for invalid in (True, 1, 0, -1, 1025, 3.0, "8", None):
            with self.assertRaises(ValueError):
                validate_selection("hybrid", "cpp", invalid)
        for strategy in ("hybrid", "short-diverse"):
            with self.assertRaises(ValueError):
                validate_selection(strategy, "python", 8)
        for strategy in ("bad", False, None):
            with self.assertRaises(ValueError):
                validate_selection(strategy, "cpp", 8)
        for bad_index in (True, 0, -1, 2.0):
            with self.assertRaises(ValueError):
                effective_selection("hybrid", 8, bad_index)
        for mode in ("first", "hybrid", "short-diverse"):
            validate_selection(mode, "cpp", 8)

    def test_audited_resume_model_clock(self):
        self.assertEqual(inherited_model_offset({}), 0)
        self.assertEqual(inherited_model_offset({"progress": {"raw_models": 7}}), 7)
        self.assertEqual(inherited_model_offset(
            {"progress": {"raw_models": 5, "selection_model_offset": 11}}), 16)
        self.assertEqual(effective_selection("hybrid", 8, 16), "short-diverse")
        self.assertEqual(effective_selection("hybrid", 8, 17), "first")
        for bad in ("bogus", [], {"progress": []},
                    {"progress": {"raw_models": True}},
                    {"progress": {"raw_models": -1}},
                    {"progress": {"selection_model_offset": "3"}},
                    {"progress": {"selection_model_offset": -5}}):
            with self.assertRaises(ValueError):
                inherited_model_offset(bad)


@unittest.skipUnless(shutil.which("g++"), "g++ required for real C++ hybrid integration")
class LiveHybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import pysat
        except ImportError:
            raise unittest.SkipTest("pinned python-sat required")
        cls.workspace = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.workspace.cleanup)
        cls.binary = Path(cls.workspace.name) / "lasso_batch"
        subprocess.run(["g++", "-O3", "-std=c++17", "-Wall", "-Wextra",
                        "-Werror", str(Path(__file__).with_name("lasso_batch.cpp")),
                        "-o", str(cls.binary)],
                       check=True, capture_output=True, timeout=30)

    def test_journal_hybrid_and_resume_preserves_clock(self):
        from lasso_search import run
        from lasso_witness import audit
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first"
            result = run(first, 4, 3, -1, [41], 1.4,
                         walker="cpp", batch_binary=self.binary,
                         witness_selection="hybrid", hybrid_every=2,
                         checkpoint_mode="journal")
            self.assertEqual(audit(first)["status"], "CHECKED")
            self.assertEqual(result["witness_selection"], "hybrid")
            self.assertEqual(result["hybrid_every"], 2)
            self.assertEqual(sum(result["selected_mode_counts"].values()),
                             result["raw_models"])
            self.assertEqual(sum(result["selected_mode_clauses"].values()),
                             result["new_witnesses"])
            self.assertEqual(sum(result["selected_mode_literals"].values()),
                             result["clause_literals_total"])
            data = json.loads((first / "manifest.json").read_text())
            self.assertEqual(data["progress"]["raw_models"], result["raw_models"])
            second = root / "second"
            resumed = run(second, 4, 3, -1, [41], 1.4,
                          walker="cpp", batch_binary=self.binary,
                          witness_selection="hybrid", hybrid_every=2,
                          resume=first, checkpoint_mode="journal")
            self.assertEqual(audit(second)["status"], "CHECKED")
            self.assertEqual(resumed["selection_model_offset"], result["raw_models"])
            self.assertEqual(sum(resumed["selected_mode_counts"].values()),
                             resumed["raw_models"])
            lines = (second / "cpp-batches.jsonl").read_text().splitlines()
            for line in lines:
                item = json.loads(line)
                self.assertEqual(item["selection_mode"], effective_selection(
                    "hybrid", 2, item["global_model_index"]))
                self.assertEqual(item["hybrid_every"], 2)
                self.assertIn(item["selection_mode"], ("first", "short-diverse"))

    def test_generational_mode_and_rejections(self):
        from lasso_search import run
        from lasso_witness import audit
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run(root / "generations", 4, 3, -1, [41], 1.5,
                         walker="cpp", batch_binary=self.binary,
                         checkpoint_mode="generations", checkpoint_seconds=0.3,
                         witness_selection="hybrid", hybrid_every=2)
            self.assertEqual(result["witness_selection"], "hybrid")
            self.assertEqual(audit(root / "generations")["status"], "CHECKED")
            with self.assertRaises(ValueError):
                run(root / "invalid-walker", 4, 3, -1, [41], 1.0,
                    walker="python", witness_selection="hybrid")
            self.assertFalse((root / "invalid-walker").exists())
            with self.assertRaises(ValueError):
                run(root / "invalid-interval", 4, 3, -1, [41], 1.0,
                    walker="cpp", witness_selection="hybrid", hybrid_every=True,
                    batch_binary=self.binary)
            self.assertFalse((root / "invalid-interval").exists())


if __name__ == "__main__":
    unittest.main()
