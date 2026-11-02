"""Independently check shortest/diverse C++ witnesses and legacy behavior."""
import json
import random
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from lasso_witness import checked_clause, geometry, selector_rows, trace


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("g++"):
            raise unittest.SkipTest("g++ unavailable")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.binary = Path(cls.temporary.name) / "lasso_batch"
        subprocess.run(["g++", "-std=c++17", "-O3", "-Wall", "-Wextra", "-Werror",
                        str(Path(__file__).with_name("lasso_batch.cpp")),
                        "-o", str(cls.binary)], check=True, capture_output=True, timeout=30)

    @staticmethod
    def policy(n, target, rng):
        return {key: rng.choice(choices)[0]
                for key, choices in selector_rows(n, target).items()}

    def scan(self, policy, n, target, masks, limit=24, mode="short-diverse", explicit=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "policy.tsv").write_text(f"{n} {target}\n" + "".join(
                " ".join(map(str, (*key, action))) + "\n"
                for key, action in sorted(policy.items())))
            (root / "masks.txt").write_text("".join(f"{m}\n" for m in masks))
            cmd = [str(self.binary), str(root / "policy.tsv"),
                   str(root / "masks.txt"), str(limit)]
            if explicit:
                cmd.append(mode)
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if output.returncode:
                return output.returncode, output.stderr
            return 0, [json.loads(line) for line in output.stdout.splitlines()]

    def test_both_orbits_source_optimum_no_subsumption_and_full_mask_accounting(self):
        rng = random.Random(20261103)
        for n, target in ((4, 3), (7, 0), (7, 3)):
            edges = n * (n - 1) // 2 - (2 if n == 7 else 0)
            for trial in range(6):
                policy = self.policy(n, target, rng)
                masks = sorted(rng.sample(range(1 << edges), min(160, 1 << edges)))
                code, data = self.scan(policy, n, target, masks)
                self.assertEqual(code, 0, data)
                report = data[-1]
                self.assertEqual(report["selection"], "short-diverse")
                self.assertTrue(report["scan_complete"])
                self.assertEqual(report["scanned_masks"], len(masks))
                obligations, bad_masks = 0, 0
                for mask in masks:
                    _, connected = geometry(n, target, mask)
                    obligations += len(connected) - 1
                    if any(trace(policy, n, target, mask, s) is not None
                           for s in connected - {target}):
                        bad_masks += 1
                self.assertEqual(report["failed_masks"], bad_masks)
                self.assertEqual(report["connected_source_obligations"], obligations)
                clauses = []
                for item in data[:-1]:
                    witness = item["witness"]
                    self.assertEqual(witness, trace(policy, n, target,
                                                    witness["mask"], witness["source"]))
                    clause = checked_clause(witness, n, target)
                    self.assertNotIn(clause, clauses)
                    clauses.append(clause)
                    _, connected = geometry(n, target, witness["mask"])
                    alternatives = [trace(policy, n, target, witness["mask"], s)
                                    for s in connected - {target}]
                    shortest = min(len(checked_clause(other, n, target))
                                   for other in alternatives if other is not None)
                    self.assertEqual(len(clause), shortest)
                self.assertEqual(report["witnesses"], len(clauses))
                sets = [set(c) for c in clauses]
                for i, x in enumerate(sets):
                    self.assertFalse(any(y < x for j, y in enumerate(sets) if i != j))

    def test_determinism_and_legacy_first_mode(self):
        rng = random.Random(20261104)
        for n, target in ((4, 3), (7, 0), (7, 3)):
            edges = n * (n - 1) // 2 - (2 if n == 7 else 0)
            masks = sorted(rng.sample(range(1 << edges), min(192, 1 << edges)))
            policy = self.policy(n, target, rng)
            a, first = self.scan(policy, n, target, masks, limit=12)
            b, again = self.scan(policy, n, target, masks, limit=12)
            self.assertEqual(a, b)
            self.assertEqual(first, again)
            a, legacy = self.scan(policy, n, target, masks, limit=12, explicit=False)
            b, explicit = self.scan(policy, n, target, masks, limit=12, mode="first")
            self.assertEqual(a, b)
            self.assertEqual(legacy, explicit)

    def test_invalid_selection_rejected(self):
        policy = self.policy(4, 3, random.Random(0))
        for bad in ("invalid", "short_diverse", ""):
            code, error = self.scan(policy, 4, 3, [41], mode=bad)
            self.assertNotEqual(code, 0)
            self.assertIn("selection", error)

    def test_solver_journal_and_configuration(self):
        try:
            from lasso_search import run
            from lasso_witness import audit
        except ModuleNotFoundError:
            raise unittest.SkipTest("pinned SAT backend unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mode in ("first", "short-diverse"):
                output = root / mode
                data = run(output, 4, 3, -1, [41], 1.5,
                           walker="cpp", batch_binary=self.binary,
                           witness_selection=mode)
                self.assertEqual(data["witness_selection"], mode)
                self.assertEqual(audit(output)["status"], "CHECKED")
                self.assertIn(data["status"], ("UNKNOWN", "UNSAT_UNCERTIFIED",
                                              "FINITE_SUITE_SAT_UNVERIFIED"))
            with self.assertRaises(ValueError):
                run(root / "forbidden", 4, 3, -1, [41], 1.0,
                    walker="python", witness_selection="short-diverse")
            with self.assertRaises(ValueError):
                run(root / "invalid", 4, 3, -1, [41], 1.0,
                    walker="cpp", witness_selection="garbage",
                    batch_binary=self.binary)


if __name__ == "__main__":
    unittest.main()
