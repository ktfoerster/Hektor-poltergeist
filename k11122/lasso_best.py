"""Diagnostic best-observed raw SAT policy on a frozen finite residual suite.

The C++ scorer is an untrusted fast ranking aid. The independently decoded
historical best policy is fully replayed in Python at finalization. It is
NEVER a claim of SAT for the terminal CNF, nor a graph-positive certificate.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from lasso_policy_quality import read_policy
from lasso_witness import geometry, selector_rows, sha, trace


_KEYS = ("n", "target", "residuals", "connected_source_obligations",
         "failed_connected_sources", "failing_residual_masks")


def independent_quality(policy_path, n, target, masks):
    """Reconstruct all source obligations without using the C++ ranking aid."""
    rows = selector_rows(n, target)
    policy = read_policy(policy_path, n, target, rows)
    obligations, failures, failed_masks = 0, 0, 0
    for mask in masks:
        _, component = geometry(n, target, mask)
        failed = False
        for source in sorted(component):
            if source == target:
                continue
            obligations += 1
            if trace(policy, n, target, mask, source) is not None:
                failures += 1
                failed = True
        failed_masks += int(failed)
    return dict(n=n, target=target, residuals=len(masks),
                connected_source_obligations=obligations,
                failed_connected_sources=failures,
                failing_residual_masks=failed_masks)


def _atomic_bytes(path, contents):
    """Do not leave a partly written best-policy file on crash."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        f.write(contents)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _canonical(obj):
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()


class BestObserved:
    def __init__(self, output, n, target, branch, masks, binary, interval=1):
        if type(interval) is not int or not 1 <= interval <= 1024:
            raise ValueError("quality interval must be integer 1..1024")
        if (not isinstance(masks, list) or not masks or
                masks != sorted(set(masks)) or
                any(type(x) is not int for x in masks)):
            raise ValueError("quality input masks must be canonical")
        self.output = Path(output)
        self.n, self.target, self.branch = n, target, branch
        self.interval = interval
        self.masks = masks
        self.binary = Path(binary).resolve(strict=True)
        self.expected_obligations = sum(
            len(geometry(n, target, mask)[1]) - 1 for mask in masks)
        self.best_rank = None
        self.best = None
        self.scored = 0
        self.improvements = 0
        self.duration = 0.0
        if not (self.output / "masks.txt").is_file():
            raise ValueError("quality requires frozen masks.txt from C++ walker")

    def consider(self, last_policy, global_model_index):
        if type(global_model_index) is not int or global_model_index < 1:
            raise ValueError("nonpositive model identifier")
        if global_model_index != 1 and global_model_index % self.interval != 0:
            return None
        started = time.monotonic()
        completed = subprocess.run(
            [str(self.binary), str(Path(last_policy).resolve()),
             str((self.output / "masks.txt").resolve())],
            capture_output=True, text=True, check=True, timeout=6)
        try:
            item = json.loads(completed.stdout)
        except ValueError as error:
            raise RuntimeError("invalid untrusted C++ quality output") from error
        if (not isinstance(item, dict) or
                set(item) != set(_KEYS) | {"schema", "type"} or
                item.get("schema") != 1 or
                item.get("type") != "frozen_policy_quality" or
                any(type(item.get(key)) is not int for key in _KEYS) or
                (item["n"], item["target"], item["residuals"],
                 item["connected_source_obligations"]) !=
                (self.n, self.target, len(self.masks),
                 self.expected_obligations) or
                not (0 <= item["failing_residual_masks"] <= len(self.masks)) or
                not (0 <= item["failed_connected_sources"] <=
                     self.expected_obligations) or
                item["failing_residual_masks"] > item["failed_connected_sources"]):
            raise RuntimeError("invalid untrusted policy quality accounting")
        self.scored += 1
        policy_sha = sha(last_policy)
        rank = (item["failing_residual_masks"], item["failed_connected_sources"],
                policy_sha)
        improved = self.best_rank is None or rank < self.best_rank
        entry = dict(model_index=global_model_index, policy_sha256=policy_sha,
                     failed_residual_masks=item["failing_residual_masks"],
                     failed_connected_sources=item["failed_connected_sources"],
                     scored_models=self.scored, improved=improved)
        with (self.output / "quality-samples.jsonl").open("a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        if improved:
            data = Path(last_policy).read_bytes()
            if hashlib.sha256(data).hexdigest() != policy_sha:
                raise RuntimeError("policy mutated while scoring")
            record = dict(schema=1, scope="historical best raw SAT policy on frozen suite; NOT terminal CNF SAT or full-graph positive",
                          n=self.n, target=self.target, branch=self.branch,
                          masks_sha256=sha(self.output / "masks.json"),
                          quality_checker_sha256=sha(self.binary),
                          policy_sha256=policy_sha,
                          source_model_index=global_model_index,
                          scoring_interval=self.interval,
                          quality={key: item[key] for key in _KEYS})
            _atomic_bytes(self.output / "best-policy.tsv", data)
            _atomic_bytes(self.output / "best-policy.json", _canonical(record))
            self.best_rank = rank
            self.best = record
            self.improvements += 1
        self.duration += time.monotonic() - started
        return entry

    def summary(self):
        return dict(quality_sampling_interval=self.interval,
                    quality_scored_raw_models=self.scored,
                    quality_improvements=self.improvements,
                    quality_sampling_seconds=self.duration,
                    best_observed_raw_quality=(self.best["quality"]
                                               if self.best is not None else None),
                    best_observed_model_index=(self.best["source_model_index"]
                                               if self.best is not None else None))


def independently_check_best(directory):
    """Fully check the recorded best table using independent literal walks.

    The result is a historical *diagnostic*, not a SAT proof for the final CNF.
    """
    root = Path(directory)
    path, manifest = root / "best-policy.tsv", root / "best-policy.json"
    if not path.is_file() and not manifest.is_file():
        return {"status": "NO_SCORED_POLICY"}
    if not path.is_file() or not manifest.is_file():
        raise ValueError("partial best-policy snapshot")
    meta = json.loads(manifest.read_text())
    needed = {"schema", "scope", "n", "target", "branch", "masks_sha256",
              "quality_checker_sha256", "policy_sha256", "source_model_index",
              "scoring_interval", "quality"}
    if set(meta) != needed or meta["schema"] != 1:
        raise ValueError("malformed best-policy evidence")
    if (type(meta["source_model_index"]) is not int or
            meta["source_model_index"] < 1 or
            type(meta["scoring_interval"]) is not int or
            not 1 <= meta["scoring_interval"] <= 1024):
        raise ValueError("best-policy model/sampling metadata")
    if sha(path) != meta["policy_sha256"] or sha(root / "masks.json") != meta["masks_sha256"]:
        raise ValueError("best-policy or frozen domain changed")
    masks = json.loads((root / "masks.json").read_text())
    if (not isinstance(masks, list) or not masks or masks != sorted(set(masks))
            or any(type(x) is not int for x in masks)):
        raise ValueError("invalid best-policy mask suite")
    independent = independent_quality(path, meta["n"], meta["target"], masks)
    if meta["quality"] != independent:
        raise ValueError("C++ selected best conflicts with independent Python replay")
    return dict(status="INDEPENDENTLY_REPLAYED_HISTORICAL_BEST", 
                scope=meta["scope"], policy_sha256=sha(path),
                source_model_index=meta["source_model_index"],
                scoring_interval=meta["scoring_interval"],
                quality=independent)
