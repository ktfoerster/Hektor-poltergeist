"""Frozen-training holdout guards and precommitted decision rule tests."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from holdout_backend_selection import (
    BACKENDS, CASES, CONTINUATION_PHASE_SALT, HOLDOUT_SOLVER_SEED,
    MODES, SOURCE_PHASE_SALT, TRAINING_FILE, TRAINING_GIT_BLOB,
    locked_training, make_phase, summarise,
)
from lasso_witness import selector_rows, sha
from lasso_phase_preferences import generate


class PreregisteredTrainingTests(unittest.TestCase):
    def test_immutable_training_and_all_eight_choices(self):
        plan = locked_training()
        self.assertEqual(plan["status"], "PREREGISTERED_BEFORE_HOLDOUT")
        self.assertEqual(plan["training_git_blob_sha1"], TRAINING_GIT_BLOB)
        self.assertEqual(plan["holdout_solver_seed"], HOLDOUT_SOLVER_SEED)
        self.assertEqual(len(plan["fixed_choices"]), 4)
        expected = {
            "t0-b0": {"cadical195": "balanced-half", "maplechrono": "shortest-half"},
            "t0-b1": {"cadical195": "shortest-half", "maplechrono": "shortest-half"},
            "t3-b0": {"cadical195": "shortest-half", "maplechrono": "all"},
            "t3-b1": {"cadical195": "balanced-half", "maplechrono": "shortest-half"},
        }
        self.assertEqual(plan["fixed_choices"], expected)
        self.assertEqual(set(plan["training_scores"]), set(expected))
        self.assertNotEqual(SOURCE_PHASE_SALT, CONTINUATION_PHASE_SALT)

    def test_tampering_is_rejected_before_search(self):
        original = TRAINING_FILE.read_bytes()
        computed = hashlib.sha1(
            f"blob {len(original)}\0".encode() + original).hexdigest()
        self.assertEqual(computed, TRAINING_GIT_BLOB)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "training.json"
            path.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                locked_training(path)
            bad = original.replace(b"41811555234", b"41811555235", 1)
            path.write_bytes(bad)
            with self.assertRaises(ValueError):
                locked_training(path)

    def test_heldout_phase_files_are_legal_and_distinct(self):
        for target, branch in CASES:
            with self.subTest(target=target, branch=branch):
                with tempfile.TemporaryDirectory() as temp:
                    a, b = Path(temp) / "source.tsv", Path(temp) / "continuation.tsv"
                    h1 = make_phase(a, target, branch, SOURCE_PHASE_SALT)
                    h2 = make_phase(b, target, branch, CONTINUATION_PHASE_SALT)
                    self.assertNotEqual(h1, h2)
                    self.assertEqual(h1, sha(a))
                    self.assertEqual(h2, sha(b))
                    keys = set(selector_rows(7, target))
                    self.assertEqual(keys, set(generate(7, target, branch, "hash",
                                                      SOURCE_PHASE_SALT)))
                    self.assertEqual(keys, set(generate(7, target, branch, "hash",
                                                      CONTINUATION_PHASE_SALT)))

    def test_summary_does_not_posthoc_choose_winning_mode(self):
        plan = locked_training()
        selected = plan["fixed_choices"]["t0-b0"]
        assert selected["cadical195"] == "balanced-half"
        assert selected["maplechrono"] == "shortest-half"
        c = dict(preregistered_choices=selected,
                 phase_checks={
                     "new_phase_vs_no_phase_cadical": {"actually_divergent": True},
                     "cadical_vs_maple_source": {"actually_divergent": True}},
                 holdout_evaluation={
                     "cadical195": {
                         "chosen_before_holdout": "balanced-half",
                         "chosen_failing_masks": 60, "full_failing_masks": 50,
                         "chosen_minus_full": 10},
                     "maplechrono": {
                         "chosen_before_holdout": "shortest-half",
                         "chosen_failing_masks": 20, "full_failing_masks": 30,
                         "chosen_minus_full": -10}},
                 continuations={backend: {
                     mode: {"finite_suite_candidates": 0,
                            "best_historical_policy": {
                                "failing_masks": 50 if mode=="all" else 20}}
                     for mode in MODES} for backend in BACKENDS})
        result = summarise({"t0-b0": c})
        self.assertEqual(result["preregistered_less_than_full"], 1)
        self.assertEqual(result["preregistered_greater_than_full"], 1)
        self.assertEqual(result["nontrivial_selected_half_comparisons"], 2)
        self.assertEqual(result["complete_finite_suite_candidates"], 0)
        self.assertEqual(result["cells"]["t0-b0"]["cadical195"]["preregistered_mode"],
                         "balanced-half")
        self.assertNotEqual(result["cells"]["t0-b0"]["cadical195"]["preregistered_mode"],
                            "shortest-half")


if __name__ == "__main__":
    unittest.main()
