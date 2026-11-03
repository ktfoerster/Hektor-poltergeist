"""Independent necessary-clause portfolio tests, corruption and solver resumption."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lasso_portfolio import build
from lasso_witness import audit, checked_clause
from test_lasso_transfer import fixture


class PortfolioTests(unittest.TestCase):
    def test_exact_deduplication_and_new_full_cnf(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root/"a")
            shutil.copytree(root/"a",root/"b")
            result=build(root/"portfolio",[root/"a",root/"b"])
            self.assertEqual(result["source_count"],2)
            self.assertEqual(result["input_witnesses"],4)
            self.assertEqual(result["deduplicated_witnesses"],2)
            self.assertEqual(result["duplicates_eliminated"],2)
            self.assertEqual(result["source_details"][1]["newly_contributed_necessary_clauses"],0)
            self.assertEqual(audit(root/"portfolio")["status"],"CHECKED")
            self.assertEqual(json.loads((root/"portfolio"/"manifest.json").read_text())["imported"]["portfolio"]["source_solver_results_inherited"],False)
            self.assertEqual(len((root/"portfolio"/"witnesses.jsonl").read_text().splitlines()),2)

    def test_reject_cross_target_branch_masks_and_malformed_input_without_output(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            fixture(root/"a")
            shutil.copytree(root/"a",root/"b")
            for expected_target,expected_branch in ((0,0),(3,1)):
                output=root/f"wrong-{expected_target}-{expected_branch}"
                with self.assertRaises(ValueError):
                    build(output,[root/"a",root/"b"],expected_target,expected_branch)
                self.assertFalse(output.exists())
            output=root/"duplicate"
            with self.assertRaises(ValueError):
                build(output,[root/"a",root/"a"])
            self.assertFalse(output.exists())
            (root/"b"/"witnesses.jsonl").write_text("malicious data\n")
            with self.assertRaises(ValueError):
                build(root/"corrupt",[root/"a",root/"b"])
            self.assertFalse((root/"corrupt").exists())

    def test_small_graph_portfolio_restart_with_audited_resume(self):
        try:
            from lasso_search import run
        except ModuleNotFoundError:
            self.skipTest("SAT backend unavailable")
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            fixture(root/"a")
            shutil.copytree(root/"a",root/"b")
            result=build(root/"combined",[root/"a",root/"b"])
            self.assertEqual(result["deduplicated_witnesses"],2)
            resumed=run(root/"continued",4,3,0,[19,35],1.4,
                        resume=root/"combined",checkpoint_mode="journal",
                        allow_audited_migration=True)
            self.assertEqual(resumed["inherited_witnesses"],2)
            self.assertEqual(audit(root/"continued")["status"],"CHECKED")
            meta=json.loads((root/"continued"/"manifest.json").read_text())
            self.assertEqual(meta["imported"]["resumed_from"]["formula_sha256"],
                             result["formula_sha256"])
            self.assertIn(resumed["status"],("UNKNOWN","UNSAT_UNCERTIFIED",
                                              "FINITE_SUITE_SAT_UNVERIFIED",
                                              "FINITE_SAT_GLOBALLY_INVALID",
                                              "VERIFIED_POSITIVE_ONE_ORBIT"))


if __name__=="__main__":
    unittest.main()
