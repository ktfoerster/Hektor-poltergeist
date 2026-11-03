"""POSIX checkpoint publication. Progress is advisory; current is the commit point.

Working files are never recovery inputs. Immutable generations retain every
committed witness and scanner log. No solver-memory restoration is claimed.
"""
import json
import os
from pathlib import Path
import shutil
import time


FILES = ("selectors.json", "masks.json", "witnesses.jsonl", "masks.txt",
         "cpp-batches.jsonl", "last-policy.tsv", "exhaustive-verifier.log",
         "best-policy.tsv", "best-policy.json", "quality-samples.jsonl")


def checkpoint_root(directory):
    root = Path(directory)
    if (root / "current").is_symlink():
        # Pin once: a concurrent publication must not mix generations.
        return (root / "current").resolve(strict=True)
    return root


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Checkpoints:
    def __init__(self, root, interval):
        self.root = Path(root)
        self.work = self.root / ".working"
        self.work.mkdir()
        self.generations = self.root / "checkpoints"
        self.generations.mkdir()
        # Persist the newly created output directory entry before any commit.
        sync_directory(self.root.parent)
        self.interval = interval
        self.last = float("-inf")
        self.number = 0

    def save(self, enc, masks, target, branch, witnesses, stats, imported,
             snapshot, force=False):
        if force or time.monotonic() - self.last >= self.interval:
            before = time.monotonic()
            self.number += 1
            name = f"{self.number:06d}"
            staging = self.generations / (name + ".tmp")
            staging.mkdir()
            for filename in FILES:
                source = self.work / filename
                if source.exists():
                    shutil.copyfile(source, staging / filename)
            copied_seconds = time.monotonic() - before
            snapshot(staging, enc, masks, target, branch, witnesses, stats, imported)
            publish_started = time.monotonic()
            # Data, generation name, then the single commit pointer, in that order.
            for path in staging.iterdir():
                with path.open("rb") as f:
                    os.fsync(f.fileno())
            sync_directory(staging)
            staging.rename(self.generations / name)
            sync_directory(self.generations)
            for path in (self.generations / name).iterdir():
                alias = self.root / path.name
                if not alias.is_symlink():
                    alias.symlink_to(Path("current") / path.name)
            temporary = self.root / "current.tmp"
            temporary.symlink_to(Path("checkpoints") / name)
            temporary.replace(self.root / "current")
            sync_directory(self.root)
            self.last = time.monotonic()
            stats["checkpoint_publish_seconds"] += copied_seconds + self.last - publish_started
            stats["checkpoint_count"] += 1
            stats["checkpoint_total_seconds"] += self.last - before
        before = time.monotonic()
        # Never used by audit/resume, deliberately not fsynced per SAT assignment.
        temporary = self.root / "progress.json.tmp"
        temporary.write_text(json.dumps({
            "schema": 1, "advisory": True,
            "committed_generation": self.number,
            "progress": stats}, sort_keys=True) + "\n")
        temporary.replace(self.root / "progress.json")
        stats["progress_seconds"] += time.monotonic() - before
