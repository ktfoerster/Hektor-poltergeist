"""Independent bounded matrix controls and branch-1 portfolio compatibility."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from lasso_portfolio_matrix import (
    BACKENDS, ARMS, compare_arms, policy_hashes, validate_options
)
from lasso_portfolio import build
from lasso_witness import audit, base_clauses, selector_rows, sha
from test_lasso_transfer import fixture


class MatrixHelpersTests(unittest.TestCase):
    def test_four_case_domains_and_valid_budget_limits(self):
        for source, cont, seed, interval in (
                (6.0, 8.0, 20261103, 8),
                (0.5, 1.0, 1, 1),
                (45, 45, 2147483647, 64)):
            validate_options(source, cont, seed, interval)
        for params in (
                (0, 8, 1, 8), (-1, 8, 1, 8),
                (46, 8, 1, 8), (8, 0, 1, 8),
                (8, 8, 0, 8), (8, 8, True, 8),
                (8, 8, 1, 0), (8, 8, 1, 65),
                (8, 8, 1, 8.0), (8, 8, 1, True),
                (8, 8, 1, "8"), (float("nan"), 8, 1, 8)):
            with self.assertRaises(ValueError):
                validate_options(*params)
        self.assertEqual(set(ARMS), {"cadical195", "maplechrono", "portfolio"})
        self.assertEqual(len(BACKENDS), 2)

    def test_best_sampled_quality_comparison_cannot_infer_feasibility(self):
        def arm(failure_count, model_count):
            return dict(
                sampled_historical_best=(
                    {"status": "NO_SCORED_POLICY"} if failure_count is None
                    else {"status": "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST",
                          "quality": {"failing_residual_masks": failure_count}}),
                raw_models=model_count, new_certified_clauses=96*model_count,
                active_search_seconds=8.0)
        cases={
            "cadical195":arm(419,15),
            "maplechrono":arm(446,14),
            "portfolio":arm(366,16)}
        result=compare_arms(cases)
        self.assertEqual(result["portfolio_improvement_vs_best_single_masks"],53)
        self.assertEqual(result["raw_SAT_assignments"]["portfolio"],16)
        self.assertIn("not a solution", result["interpretation"])
        cases["portfolio"]=arm(None,0)
        self.assertIsNone(compare_arms(cases)["portfolio_improvement_vs_best_single_masks"])
        cases["portfolio"]["sampled_historical_best"]={"status":"unchecked"}
        with self.assertRaises(RuntimeError):
            compare_arms(cases)

    def test_trajectory_hash_sequence_and_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(policy_hashes(root),[])
            logs=root/"cpp-batches.jsonl"
            good=[{"global_model_index":i,"policy_sha256":str(k)*64}
                  for i,k in enumerate("abc",start=1)]
            logs.write_text("".join(json.dumps(x)+"\n" for x in good))
            self.assertEqual(policy_hashes(root),[str(c)*64 for c in "abc"])
            for malformed in (
                [{"global_model_index":1,"policy_sha256":"z"*64}],
                [{"global_model_index":1,"policy_sha256":"abc"}],
                [{"global_model_index":2,"policy_sha256":"a"*64}],
                [{"global_model_index":1,"policy_sha256":"a"*64},
                 {"global_model_index":3,"policy_sha256":"b"*64}]):
                logs.write_text("".join(json.dumps(x)+"\n" for x in malformed))
                with self.assertRaises(RuntimeError):
                    policy_hashes(root)

    @staticmethod
    def switch_fixture_to_branch_one(root):
        meta=json.loads((root/"manifest.json").read_text())
        n,target=meta["n"],meta["target"]
        rows=selector_rows(n,target)
        witnesses=[json.loads(line) for line in (root/"witnesses.jsonl").read_text().splitlines()]
        clauses=list(base_clauses(n,target,1,rows))+[item["clause"] for item in witnesses]
        body="".join(" ".join(map(str,x))+" 0\n" for x in clauses)
        formula=f"p cnf {meta['variables']} {len(clauses)}\n"+body
        (root/"formula.cnf").write_text(formula)
        meta.update(branch=1, clauses=len(clauses),
                    clause_body_sha256=hashlib.sha256(body.encode()).hexdigest())
        meta["sha256"]["formula.cnf"]=sha(root/"formula.cnf")
        (root/"manifest.json").write_text(json.dumps(meta,sort_keys=True)+"\n")
        assert audit(root)["status"]=="CHECKED"

    def test_portfolio_respects_both_first_hop_branches(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            fixture(root/"s0")
            shutil.copytree(root/"s0",root/"s1")
            self.switch_fixture_to_branch_one(root/"s1")
            with self.assertRaises(ValueError):
                build(root/"cross-branch",[root/"s0",root/"s1"],
                      expected_target=3, expected_branch=1)
            self.assertFalse((root/"cross-branch").exists())
            shutil.copytree(root/"s1",root/"s1copy")
            merged=build(root/"same-branch",[root/"s1",root/"s1copy"],
                         expected_target=3,expected_branch=1)
            self.assertEqual(merged["branch"],1)
            self.assertEqual(merged["source_count"],2)
            self.assertEqual(merged["deduplicated_witnesses"],2)
            self.assertEqual(audit(root/"same-branch")["status"],"CHECKED")


if __name__=="__main__":
    unittest.main()
