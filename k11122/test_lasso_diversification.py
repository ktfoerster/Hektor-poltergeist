"""Independent tests for phase-only SAT diversification and policy-hash evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from lasso_phase_preferences import generate, distinguished_row
from lasso_divergence import first_divergence
from lasso_search import CapturedPolicy, run
from lasso_witness import audit, selector_rows, sha
from sat_search import partition, write_policy, read_phase_policy, apply_phase_policy


class PhasePreferencesTests(unittest.TestCase):
    def test_complete_legal_branch_compatible_and_deterministic(self):
        for n, target in ((4, 3), (7, 0), (7, 3)):
            rows = selector_rows(n, target)
            for branch in (0, 1):
                row, hop = distinguished_row(n, target, branch)
                for variant in ("first", "last", "hash"):
                    policy = generate(n, target, branch, variant, 20261103)
                    self.assertEqual(set(policy), set(rows))
                    self.assertTrue(all(action in dict(rows[key])
                                        for key, action in policy.items()))
                    self.assertEqual(policy[row] // 2, hop)
            self.assertNotEqual(generate(n, target, 0, "first"),
                                generate(n, target, 0, "last"))
            self.assertEqual(generate(n, target, 0, "hash", 4),
                             generate(n, target, 0, "hash", 4))
        for bad_branch in (-1, 2, True, "0"):
            with self.assertRaises(ValueError):
                generate(7, 0, bad_branch, "hash")
        for bad_variant in ("MIN", None, "frozen"):
            with self.assertRaises(ValueError):
                generate(7, 0, 0, bad_variant)
        for bad_salt in (-1, True, 2**31, "5", 1.0):
            with self.assertRaises(ValueError):
                generate(7, 0, 0, "hash", bad_salt)

    def test_phase_preferences_add_no_constraints_even_on_branch_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            enc = CapturedPolicy(4, 3, directory / "clauses.body")
            try:
                partition(enc, 0)
                before = (enc.top, enc.clause_count, enc.fingerprint.hexdigest())
                path = directory / "phase.tsv"
                preferred = generate(4, 3, 0, "hash", 5)
                write_policy(path, 4, 3, preferred)
                self.assertEqual(read_phase_policy(path, enc), preferred)
                info = apply_phase_policy(path, enc)
                after = (enc.top, enc.clause_count, enc.fingerprint.hexdigest())
                self.assertEqual(before, after)
                self.assertEqual(info["rows"], len(enc.rows))
                branch_key = distinguished_row(4, 3, 0)[0]
                forced_other = -enc.selector(branch_key, preferred[branch_key])
                self.assertTrue(enc.solver.solve(assumptions=[forced_other]))
                self.assertNotEqual(enc.policy()[branch_key], preferred[branch_key])
            finally:
                enc.close()

    def test_prevalidation_does_not_create_output_on_malformed_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            bad = directory / "bad.tsv"
            bad.write_text("4 3\n")
            output = directory / "should-not-exist"
            with self.assertRaisesRegex(ValueError, "incomplete"):
                run(output, 4, 3, -1, [41], 1,
                    phase_policy=bad)
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, "existing"):
                run(output, 4, 3, -1, [41], 1,
                    phase_policy=directory / "missing.tsv")
            self.assertFalse(output.exists())

    def test_both_checkpoint_modes_preserve_exact_hint_and_full_cnf(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "phase.tsv"
            write_policy(path, 4, 3, generate(4, 3, 0, "last"))
            digest = sha(path)
            for mode in ("journal", "generations"):
                output = directory / mode
                result = run(output, 4, 3, -1, [41], 1.4,
                             phase_policy=path, checkpoint_mode=mode,
                             checkpoint_seconds=0.3)
                self.assertEqual(result["phase_preference"]["sha256"], digest)
                self.assertEqual(result["phase_preference"]["semantics"],
                                 "branching phases only, no clauses or assumptions")
                self.assertEqual(sha(output / "phase-policy.tsv"), digest)
                self.assertEqual(audit(output)["status"], "CHECKED")
                meta = json.loads((output / "manifest.json").read_text())
                self.assertEqual(meta["sha256"]["phase-policy.tsv"], digest)
                self.assertEqual(meta["progress"]["phase_preference"]["sha256"], digest)


class DivergenceTests(unittest.TestCase):
    def test_early_and_late_divergence_and_identical_prefixes(self):
        a, b, c = "a" * 64, "b" * 64, "c" * 64
        common = first_divergence([a, b, c], [a, b])
        self.assertFalse(common["actually_divergent"])
        self.assertEqual(common["shared_identical_prefix_models"], 2)
        different = first_divergence([a, b, c], [a, c, b])
        self.assertTrue(different["actually_divergent"])
        self.assertEqual(different["first_divergent_model_in_common_prefix"], 2)
        self.assertEqual(first_divergence([a], [b])["first_divergent_model_in_common_prefix"], 1)
        self.assertFalse(first_divergence([], [b])["actually_divergent"])
        for invalid in ([0], ["g" * 64], ["A" * 64], ["a" * 63]):
            with self.assertRaises(ValueError):
                first_divergence([a], invalid)


if __name__ == "__main__":
    unittest.main()
