"""Bounded search-only clocks, observed solver counters and last-policy diagnostics."""
import json
from pathlib import Path
import tempfile
import unittest

from lasso_effort import initialize, observe, KEYS
from lasso_policy_quality import read_policy, score
from lasso_witness import selector_rows, audit


class EffortTests(unittest.TestCase):
    def test_same_worker_new_worker_and_timeout_accounting(self):
        stats = {}
        previous = initialize(stats)
        def sample(generation, conflicts, decisions, propagations, restarts):
            nonlocal previous
            payload = {"worker_generation": generation, "solver": dict(
                conflicts=conflicts, decisions=decisions,
                propagations=propagations, restarts=restarts)}
            previous = observe(stats, previous, payload)
        sample(1, 2, 3, 5, 1)
        sample(1, 5, 7, 12, 2)
        self.assertEqual(stats["observed_solver_effort"],
                         dict(conflicts=5, decisions=7, propagations=12, restarts=2))
        self.assertEqual(stats["solver_effort_samples"], 2)
        previous = observe(stats, previous,
                           {"bounded_timeout": True, "worker_generation": 1})
        self.assertIsNone(previous)
        self.assertEqual(stats["unsampled_bounded_timeouts"], 1)
        sample(2, 9, 11, 14, 2)
        self.assertEqual(stats["observed_solver_effort"],
                         dict(conflicts=14, decisions=18, propagations=26, restarts=4))
        self.assertEqual(stats["solver_effort_worker_generations"], 2)
        self.assertEqual(stats["solver_effort_samples"], 3)

    def test_reject_corrupt_or_decreasing_statistics(self):
        stats = {}
        previous = initialize(stats)
        with self.assertRaises(ValueError):
            observe(stats, previous, {"worker_generation": True, "solver": {}})
        with self.assertRaises(ValueError):
            observe(stats, previous, {"worker_generation": 1, "solver":
                                     {k: -1 for k in KEYS}})
        a = observe(stats, previous, {"worker_generation": 3, "solver":
                                     {k: 8 for k in KEYS}})
        with self.assertRaises(ValueError):
            observe(stats, a, {"worker_generation": 3, "solver":
                              {k: 7 for k in KEYS}})
        with self.assertRaises(ValueError):
            observe(stats, a, {"worker_generation": 2, "solver":
                              {k: 20 for k in KEYS}})


class QualityTests(unittest.TestCase):
    def test_strict_policy_translation(self):
        rows = selector_rows(4, 3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.tsv"
            policy = {key: choices[0][0] for key, choices in rows.items()}
            valid = "4 3\n" + "".join(
                " ".join(map(str, (*key, value))) + "\n"
                for key, value in sorted(policy.items()))
            path.write_text(valid)
            self.assertEqual(read_policy(path, 4, 3, rows), policy)
            for bad in (valid.replace("4 3\n", "4 0\n", 1),
                        valid.splitlines()[0] + "\n" + "\n".join(valid.splitlines()[2:]),
                        valid + valid.splitlines()[1] + "\n",
                        valid.replace(valid.splitlines()[1],
                                      valid.splitlines()[1].rsplit(" ",1)[0] + " 999",1)):
                path.write_text(bad)
                with self.assertRaises(ValueError):
                    read_policy(path, 4, 3, rows)


try:
    from lasso_search import run
    from test_lasso_transfer import fixture
    from sat_search import BooleanEncoding
    import pysat
    BACKEND = True
except ModuleNotFoundError:
    BACKEND = False


@unittest.skipUnless(BACKEND, "requires pinned Python-SAT backend")
class LiveBudgetTests(unittest.TestCase):
    def test_search_only_and_default_total_both_preserve_audits(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            fixture(directory / "source")
            for scope in ("search", "total"):
                output = directory / scope
                info = run(output, 4, 3, 1, [19, 35], 1.1,
                           transfer_opposite_bundle=directory / "source",
                           allow_audited_migration=True,
                           checkpoint_mode="journal", budget_scope=scope)
                self.assertEqual(info["budget_scope"], scope)
                self.assertEqual(info["transfer_clauses"], 1)
                self.assertGreater(info["preparation_seconds"], 0)
                self.assertGreaterEqual(info["total_wall_seconds"],
                                        info["preparation_seconds"])
                self.assertGreaterEqual(info["total_wall_seconds"], info["elapsed_seconds"])
                self.assertEqual(audit(output)["status"], "CHECKED")
                self.assertEqual(info["solver_effort_samples"],
                                 info["solver_effort_samples"])
                self.assertTrue(all(k in info["observed_solver_effort"] for k in KEYS))
                scored = score(output)
                self.assertIn(scored["status"], ("EVALUATED_RAW_POLICY",
                                                 "FINITE_SUITE_PASS_ONLY", "NO_RAW_POLICY"))
                if scored["status"] != "NO_RAW_POLICY":
                    self.assertGreaterEqual(scored["connected_source_obligations"],
                                            scored["failed_connected_sources"])
                    self.assertEqual(scored["residuals"], 2)
                self.assertLess(info["elapsed_seconds"], 2.5)

    def test_generations_search_scope_and_invalid_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / "generations"
            info = run(out, 4, 3, -1, [19, 35], 1.2,
                       budget_scope="search", checkpoint_mode="generations",
                       checkpoint_seconds=0.3)
            self.assertEqual(info["budget_scope"], "search")
            self.assertGreater(info["preparation_seconds"], 0)
            self.assertEqual(audit(out)["status"], "CHECKED")
            for bad in (True, "", "active", None):
                destination = root / ("bad" + str(bad))
                with self.assertRaises(ValueError):
                    run(destination, 4, 3, -1, [19, 35], 1.0, budget_scope=bad)
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
