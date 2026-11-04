"""Verified selective-portfolio clause soundness, dominance and resume tests."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lasso_clause_selector import _minimal, select_clauses
from lasso_portfolio import build
from lasso_witness import audit, sha
from test_lasso_transfer import fixture


class SelectivePortfolioTests(unittest.TestCase):
    def test_exact_dominance_certificates_and_legal_subset(self):
        clauses = [(-3, -2, -1), (-2, -1), (-9, -4), (-4,),
                   (-8, -3, -2, -1), (-50,), (-51, -50)]
        entries = [dict(clause=c, source=i % 2, mask=i) for i, c in enumerate(clauses)]
        minimal, dominated = _minimal(entries)
        self.assertEqual(minimal, {1, 3, 5})
        self.assertEqual(len(dominated), 4)
        for weak, strong in dominated.items():
            self.assertIn(strong, minimal)
            self.assertLessEqual(set(entries[strong]["clause"]),
                                 set(entries[weak]["clause"]))
        for mode in ("lossless", "shortest-half", "balanced-half"):
            chosen, dominated_again = select_clauses(entries, mode)
            self.assertEqual(dominated_again, dominated)
            self.assertTrue(chosen.issubset(minimal))
            self.assertEqual(len(chosen), 3 if mode == "lossless" else 3)

    def test_full_lossless_shortest_and_balanced_checkpoint_integrity(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root / "first")
            shutil.copytree(root / "first", root / "second")
            sources = [root / "first", root / "second"]
            full = build(root / "all", sources, 3, 0)
            self.assertEqual(full["deduplicated_witnesses"], 2)
            self.assertEqual(full["duplicates_eliminated"], 2)
            full_witnesses = [json.loads(x)["clause"] for x in
                              (root / "all" / "witnesses.jsonl").read_text().splitlines()]
            for mode, expected in (("lossless", 2), ("shortest-half", 1),
                                   ("balanced-half", 1)):
                output = root / mode
                report = build(output, sources, 3, 0, selection=mode)
                self.assertEqual(report["selection"], mode)
                self.assertEqual(report["deduplicated_witnesses"], expected)
                self.assertEqual(report["unique_before_selection"], 2)
                self.assertEqual(report["duplicates_eliminated"], 2)
                self.assertEqual(report["exact_equivalence_to_full"], mode == "lossless")
                self.assertEqual(audit(output)["status"], "CHECKED")
                clauses = [json.loads(x)["clause"] for x in
                           (output / "witnesses.jsonl").read_text().splitlines()]
                self.assertTrue(all(clause in full_witnesses for clause in clauses))
                meta = json.loads((output / "manifest.json").read_text())
                self.assertFalse(meta["imported"]["portfolio"]["source_solver_results_inherited"])
                self.assertEqual(meta["sha256"]["dominance.jsonl"], sha(output / "dominance.jsonl"))

    def test_bad_modes_and_modified_source_refuse_to_create_output(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root / "first")
            shutil.copytree(root / "first", root / "second")
            for value in ("bogus", 17, None):
                with self.assertRaises(ValueError):
                    build(root / "invalid", [root / "first", root / "second"],
                          3, 0, selection=value)
                self.assertFalse((root / "invalid").exists())
            modified = root / "second" / "witnesses.jsonl"
            modified.write_text("not valid JSON\n")
            with self.assertRaises(ValueError):
                build(root / "corrupt", [root / "first", root / "second"],
                      3, 0, selection="balanced-half")
            self.assertFalse((root / "corrupt").exists())

    def test_selected_checkpoint_resumes_with_full_recheck(self):
        try:
            from lasso_search import run
        except ModuleNotFoundError:
            self.skipTest("pinned Python-SAT unavailable")
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root / "first")
            shutil.copytree(root / "first", root / "second")
            selected = build(root / "selected", [root / "first", root / "second"],
                             3, 0, selection="balanced-half")
            stats = run(root / "continued", 4, 3, 0, [19, 35], 1.2,
                        resume=root / "selected", checkpoint_mode="journal",
                        allow_audited_migration=True)
            self.assertEqual(stats["inherited_witnesses"],
                             selected["deduplicated_witnesses"])
            self.assertEqual(audit(root / "continued")["status"], "CHECKED")


if __name__ == "__main__":
    unittest.main()
