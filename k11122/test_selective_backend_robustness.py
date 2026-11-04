"""Controlled selective-portfolio cross-backend comparison invariants."""
import json
from pathlib import Path
import tempfile
import unittest

from selective_backend_robustness import (
    SELECTORS, SOURCE_BACKENDS, compare_sources, score,
    validate_selector_portfolios, summarize)


class RobustnessTests(unittest.TestCase):
    def test_same_certified_sources_and_half_cap(self):
        full={"selection":"all","target":0,"branch":1,
              "deduplicated_witnesses":41}
        short={"selection":"shortest-half","target":0,"branch":1,
               "unique_before_selection":41,"deduplicated_witnesses":21,
               "exact_equivalence_to_full":False,
               "status":"INDEPENDENTLY_AUDITED_PORTFOLIO"}
        bal={**short,"selection":"balanced-half"}
        self.assertEqual(validate_selector_portfolios(
            {"all":full,"shortest-half":short,"balanced-half":bal},0,1),41)
        for mutation in (
                {**short,"deduplicated_witnesses":22},
                {**short,"target":3},
                {**short,"exact_equivalence_to_full":True},
                {**short,"status":"UNKNOWN"},
                {**short,"unique_before_selection":40}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_selector_portfolios(
                    {"all":full,"shortest-half":mutation,"balanced-half":bal},0,1)

    def test_divergence_requires_actual_complete_policy_hash(self):
        def line(index,word):
            return {"global_model_index":index,"policy_sha256":word*64}
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            a=root/"a";b=root/"b"
            a.mkdir();b.mkdir()
            (a/"cpp-batches.jsonl").write_text("".join(
                json.dumps(line(i,"a" if i==1 else "b"))+"\n" for i in range(1,4)))
            (b/"cpp-batches.jsonl").write_text((a/"cpp-batches.jsonl").read_text())
            result=compare_sources(a,b)
            self.assertFalse(result["actually_divergent"])
            self.assertEqual(result["common_prefix_checked"],3)
            values=[line(1,"c"),line(2,"b"),line(3,"b")]
            (b/"cpp-batches.jsonl").write_text("".join(
                json.dumps(x)+"\n" for x in values))
            result=compare_sources(a,b)
            self.assertTrue(result["actually_divergent"])
            self.assertEqual(result["common_prefix_checked"],3)
            (b/"cpp-batches.jsonl").write_text("invalid JSON\n")
            with self.assertRaises(ValueError):
                compare_sources(a,b)

    def test_score_does_not_promote_last_policy_or_solver_status(self):
        no={"best_historical_raw_policy":{"status":"NO_SCORED_POLICY"}}
        self.assertIsNone(score(no))
        data={"best_historical_raw_policy":{
            "status":"INDEPENDENTLY_REPLAYED_HISTORICAL_BEST",
            "policy_sha256":"f"*64,"source_model_index":17,
            "quality":{"failing_residual_masks":99,
                       "failed_connected_sources":125}}}
        self.assertEqual(score(data)["failing_masks"],99)
        self.assertEqual(score(data)["observed_raw_model"],17)
        bad={"best_historical_raw_policy":{"status":"UNSAT"}}
        with self.assertRaises(ValueError):
            score(bad)

    def test_summary_preserves_each_case_and_backend_separately(self):
        reports={}
        for mode,count in zip(SELECTORS,(100,50,50)):
            reports[mode]={"deduplicated_witnesses":count}
        continuations={}
        for backend in SOURCE_BACKENDS:
            continuations[backend]={mode:{
                "last_best_sampled_historical_invalid_policy":{
                    "failing_masks":100 if mode=="all" else 90},
                "status":"UNKNOWN","finite_suite_candidates":0}
                for mode in SELECTORS}
        case={"source_trajectory_divergence":{"actually_divergent":False},
              "portfolios":reports,"continuations":continuations,
              "continuation_backend_divergence":{
                  mode:{"actually_divergent":False} for mode in SELECTORS}}
        got=summarize({"t0-b1":case})
        self.assertFalse(got["t0-b1"]["actual_source_divergence"])
        self.assertEqual(got["t0-b1"]["selected_clause_counts"]["shortest-half"],50)
        self.assertEqual(got["t0-b1"]["finite_suite_candidates"],0)
        self.assertEqual(set(got["t0-b1"]["best_sampled_failed_masks"]),set(SOURCE_BACKENDS))


if __name__=="__main__":
    unittest.main()
