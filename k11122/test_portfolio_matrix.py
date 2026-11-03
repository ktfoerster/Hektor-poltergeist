"""Regression coverage for the four-case certified multi-solver matrix."""
import json
from pathlib import Path
import tempfile
import unittest

from lasso_divergence import first_divergence
from portfolio_matrix import CASES, BACKENDS, trajectory


class MatrixTests(unittest.TestCase):
    def test_exact_target_orbit_first_hop_partition_matrix(self):
        self.assertEqual(CASES, ((0, 0), (0, 1), (3, 0), (3, 1)))
        self.assertEqual(BACKENDS, ("cadical195", "maplechrono"))
        self.assertEqual(len(set(CASES)), 4)

    def test_complete_policy_hash_sequence_diverges_or_has_shared_prefix(self):
        a, b, c = "a"*64, "b"*64, "c"*64
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            root.mkdir(exist_ok=True)
            (root / "cpp-batches.jsonl").write_text(
                "".join(json.dumps({"global_model_index": idx,
                                     "policy_sha256": h})+"\n"
                        for idx, h in enumerate([a,b,c], start=1)))
            self.assertEqual(trajectory(root), [a,b,c])
            self.assertEqual(first_divergence(trajectory(root), [a,c,b])
                             ["first_divergent_model_in_common_prefix"], 2)
            self.assertFalse(first_divergence(trajectory(root), [a,b])
                             ["actually_divergent"])

    def test_corrupt_or_gapped_model_hashes_fail_closed(self):
        a,b = "a"*64, "b"*64
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            records=[
                [{"global_model_index":1,"policy_sha256":a},
                 {"global_model_index":3,"policy_sha256":b}],
                [{"global_model_index":1,"policy_sha256":a},
                 {"global_model_index":1,"policy_sha256":b}],
                [{"global_model_index":1,"policy_sha256":"not-a-hash"}],
                [{"global_model_index":1,"policy_sha256":b.upper()}],
                [{"global_model_index":True,"policy_sha256":a}],
            ]
            for data in records:
                (root/"cpp-batches.jsonl").write_text(
                    "".join(json.dumps(item)+"\n" for item in data))
                with self.assertRaises(ValueError):
                    trajectory(root)


if __name__=="__main__":
    unittest.main()
