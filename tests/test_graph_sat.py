import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import graph_sat as g  # noqa: E402


class GraphSatTests(unittest.TestCase):
    def test_edges_and_cnf(self):
        self.assertEqual(g.graph_edges(3, 0), [])
        self.assertEqual(g.graph_edges(3, 7), [(0, 1), (0, 2), (1, 2)])
        self.assertEqual(len(g.colour_cnf(2, [(0, 1)])), 11)
        self.assertIn("p cnf 6 11", g.dimacs(2, g.colour_cnf(2, [(0, 1)])))

    def test_independent_graph_checker(self):
        self.assertTrue(g.brute_three_colours(3, g.graph_edges(3, 7)))
        self.assertFalse(g.brute_three_colours(4, g.graph_edges(4, 63)))
        self.assertTrue(g.brute_three_colours(4, []))

    def test_model_validation(self):
        edges = [(0, 1)]
        self.assertEqual(g.validate_witness(2, edges, [1, 5]), [0, 1])
        with self.assertRaises(ValueError):
            g.validate_witness(2, edges, [1, 4])

    def test_shards_cover_disjoint_interval(self):
        shards = [g.shard_masks(23, 99, i, 4) for i in range(4)]
        self.assertEqual(len(set().union(*map(set, shards))), 99)
        self.assertEqual(sorted(sum(shards, [])), list(range(23, 122)))

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "experiment.json"
            valid = {
                "experiment": "graph-3colourability-demo",
                "vertices": 5,
                "start_mask": 0,
                "graph_count": 1024,
                "shard_count": 4,
            }
            p.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(g.parse_config(p), valid)
            for invalid in (dict(valid, vertices=True), dict(valid, graph_count=1025), dict(valid, shard_count=3)):
                p.write_text(json.dumps(invalid), encoding="utf-8")
                with self.assertRaises(ValueError):
                    g.parse_config(p)


if __name__ == "__main__":
    unittest.main()
