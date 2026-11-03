"""Independent semantic, corruption and live transfer tests for K11122."""
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

from lasso_witness import (audit, base_clauses, branch_clause, checked_clause,
                           geometry, selector_rows, sha, trace)
from lasso_transfer import transfer


def fixture(root):
    n, target, branch = 4, 3, 0
    rows = selector_rows(n, target)
    policy = {key: values[0][0] for key, values in rows.items()}
    policy[(0, 6, -1, 0)] = 2  # branch 0: source 0's first hop is vertex 1
    policy[(0, 6, 2, 0)] = 4  # mask 19: source 2 cycles via 0, independent of branch
    policy[(0, 6, 1, 0)] = 2  # mask 35: source 0 cycles via restricted injection
    witnesses = []
    for mask, source in ((19, 2), (35, 0)):
        w = trace(policy, n, target, mask, source)
        assert w is not None, (mask, source)
        witnesses.append({"witness": w, "clause": checked_clause(w, n, target, rows)})
    root.mkdir()
    (root / "selectors.json").write_text(json.dumps(
        [[*key, [[a, var] for a, var in choices]] for key, choices in rows.items()]) + "\n")
    (root / "masks.json").write_text("[19, 35]\n")
    (root / "witnesses.jsonl").write_text("".join(
        json.dumps(item, sort_keys=True) + "\n" for item in witnesses))
    clauses = list(base_clauses(n, target, branch, rows)) + [x["clause"] for x in witnesses]
    body = "".join(" ".join(map(str, c)) + " 0\n" for c in clauses)
    (root / "formula.cnf").write_text(
        f"p cnf {sum(len(v) for v in rows.values())} {len(clauses)}\n" + body)
    meta = dict(schema=1, encoding="source-reachable-lasso-v1", n=n,
                target=target, branch=branch, masks=2,
                variables=sum(len(v) for v in rows.values()), clauses=len(clauses),
                witnesses=2, clause_body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                source_sha256={"old-synthesizer": "a" * 64})
    meta["sha256"] = {name: sha(root / name) for name in
                       ("formula.cnf", "selectors.json", "masks.json", "witnesses.jsonl")}
    (root / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    assert audit(root)["witnesses"] == 2
    return rows


class TransferTests(unittest.TestCase):
    def test_sound_cross_branch_vacuity_and_no_source_restriction_import(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "source"
            rows = fixture(root)
            clauses, records = [], []
            result = transfer(root, 4, 3, 1, [19, 35], clauses.append, records.append)
            self.assertEqual(result["source_witnesses"], 2)
            self.assertEqual(result["transferred"], 1)
            self.assertEqual(result["branch_vacuous"], 1)
            self.assertEqual(result["duplicate"], 0)
            self.assertEqual(clauses, [checked_clause(records[0]["witness"], 4, 3, rows)])
            self.assertEqual(records[0]["witness"]["mask"], 19)
            allowed = set(branch_clause(4, 3, 1, rows))
            self.assertTrue(allowed.isdisjoint({-lit for lit in clauses[0]}))
            rng = random.Random(20261103)
            successes = 0
            for _ in range(250):
                policy = {key: rng.choice(choices)[0] for key, choices in rows.items()}
                policy[(0, 6, -1, 0)] = 4 + rng.randrange(2)
                selected = {dict(rows[k])[a] for k, a in policy.items()}
                satisfied = any(-lit not in selected for lit in clauses[0])
                if trace(policy, 4, 3, 19, 2) is None:
                    successes += 1
                    self.assertTrue(satisfied, "a necessary clause blocked a delivering policy")
            self.assertGreater(successes, 0)

    def test_provenance_and_corruption_controls(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "source"
            fixture(root)
            called = []
            for n, target, branch, masks in (
                (4, 3, 0, [19, 35]), (4, 0, 1, [19, 35]),
                (7, 3, 1, [19, 35]), (4, 3, 1, [19]),
                (4, 3, 1, [35, 19]), (4, 3, 2, [19, 35])):
                with self.assertRaises(ValueError):
                    transfer(root, n, target, branch, masks,
                             called.append, called.append)
                self.assertEqual(called, [])
            with self.assertRaises(ValueError):
                transfer(root, 4, 3, 1, [19, 35], called.append, called.append,
                         expected_source_hashes={"changed": "b" * 64})
            self.assertEqual(called, [])
            valid = transfer(root, 4, 3, 1, [19, 35],
                             lambda _: None, lambda _: None,
                             expected_source_hashes={"changed": "b" * 64},
                             allow_audited_migration=True)
            self.assertIn("explicit", valid["migration"])
            witness_file = root / "witnesses.jsonl"
            lines = witness_file.read_text().splitlines()
            forged = json.loads(lines[0])
            forged["clause"] = [-1]
            lines[0] = json.dumps(forged)
            witness_file.write_text("\n".join(lines) + "\n")
            meta = json.loads((root / "manifest.json").read_text())
            meta["sha256"]["witnesses.jsonl"] = sha(witness_file)
            (root / "manifest.json").write_text(json.dumps(meta))
            with self.assertRaises(ValueError):
                transfer(root, 4, 3, 1, [19, 35],
                         called.append, called.append, allow_audited_migration=True)

    def test_live_journal_generation_and_cli_validation(self):
        try:
            from lasso_search import run
        except ModuleNotFoundError:
            self.skipTest("pinned SAT backend unavailable")
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root / "source")
            for mode in ("journal", "generations"):
                output = root / mode
                result = run(output, 4, 3, 1, [19, 35], 1.5,
                             transfer_opposite_bundle=root / "source",
                             allow_audited_migration=True,
                             checkpoint_mode=mode, checkpoint_seconds=0.3)
                self.assertEqual(result["inherited_witnesses"], 1)
                self.assertEqual(result["transfer_clauses"], 1)
                self.assertEqual(result["transfer_branch_vacuous"], 1)
                self.assertEqual(audit(output)["status"], "CHECKED")
                if mode == "journal":
                    meta = json.loads((output / "journal.json").read_text())
                else:
                    meta = json.loads((output / "current" / "manifest.json").read_text())
                info = meta["imported"]["opposite_branch_certificates"]
                self.assertEqual(info["source_witnesses"], 2)
                self.assertEqual(info["transferred"], 1)
                self.assertEqual(info["branch_vacuous"], 1)
            with self.assertRaises(ValueError):
                run(root / "bad", 4, 3, -1, [19, 35], 1.0,
                    transfer_opposite_bundle=root / "source")
            self.assertFalse((root / "bad").exists())
            with self.assertRaises(ValueError):
                run(root / "bad2", 4, 3, 1, [19, 35], 1.0,
                    resume=root / "journal",
                    transfer_opposite_bundle=root / "source")
            self.assertFalse((root / "bad2").exists())


if __name__ == "__main__":
    unittest.main()
