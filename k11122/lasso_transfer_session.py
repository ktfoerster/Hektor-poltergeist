"""Same-process, content-addressed cache of independently audited lasso transfers.

The cache is *not* a portable proof or an external trust root. Every instance
is created by full CNF reconstruction and every witness's independent replay.
On reuse it verifies the original immutable input hashes, replays only those
already certified necessary clause/witness pairs into a new destination, and
the destination performs its own independent complete CNF audit.
"""
from dataclasses import dataclass
import json
from pathlib import Path

from lasso_transfer import transfer
from lasso_witness import sha

_SEAL = object()
_NAMES = ("manifest.json", "formula.cnf", "selectors.json", "masks.json",
          "witnesses.jsonl")


@dataclass(frozen=True, slots=True)
class SessionTransfer:
    source_path: Path
    n: int
    target: int
    destination_branch: int
    masks: tuple
    entries: tuple
    attested_source_hashes: tuple
    certification: dict
    _seal: object

    def emit(self, n, target, branch, masks, insert, record,
             expected_source_hashes=None, allow_audited_migration=False):
        """Reuse a certificate only in the creating Python process.

        No source semantic checker is skipped at *certification time*; no
        incomplete policy/branch assumptions or raw solver clauses enter here.
        """
        if self._seal is not _SEAL:
            raise ValueError("untrusted cache object: call certify_session")
        if (type(n) is not int or type(target) is not int or
                type(branch) is not int or
                (n, target, branch) !=
                (self.n, self.target, self.destination_branch)):
            raise ValueError("cache graph/target/opposite branch mismatch")
        if (not isinstance(masks, list) or
                tuple(masks) != self.masks or
                any(type(x) is not int for x in masks)):
            raise ValueError("cache frozen mask mismatch")
        if (expected_source_hashes is not None and
                expected_source_hashes != self.certification["source_dependency_hashes"]
                and not allow_audited_migration):
            raise ValueError("cache source dependencies require explicit migration")
        # Cheap content-addressed recheck, not a second semantic replay.
        for name, original in self.attested_source_hashes:
            if sha(self.source_path / name) != original:
                raise ValueError("cache source changed: " + name)
        if self.source_path.is_symlink():
            raise ValueError("cache source root must not be replaced by symlink")
        for clause, line in self.entries:
            insert(list(clause))
            record(json.loads(line))
        details = dict(self.certification)
        details.update(
            cache_mode="same_process_fully_audited_then_reused",
            cache_semantic_audits_this_import=0,
            cache_hash_checked_files=len(self.attested_source_hashes),
            cache_certified_witnesses=len(self.entries),
            cache_source_content_sha256=dict(self.attested_source_hashes),
            cache_is_portable_proof=False,
        )
        return details


def certify_session(source_bundle, n, target, destination_branch, masks,
                    expected_source_hashes=None, allow_audited_migration=False):
    """Create an authenticated-in-process snapshot by invoking the ORIGINAL
    independent transfer checker once, with no SAT or policy restrictions."""
    source = Path(source_bundle).resolve(strict=True)
    if not source.is_dir():
        raise ValueError("source bundle must be a directory")
    # The input bundle itself is fully reconstructed by transfer->audit;
    # then every witness is independently checked again before caching it.
    if any(not (source / x).is_file() for x in _NAMES):
        raise ValueError("incomplete independently auditable source bundle")
    before = tuple((name, sha(source / name)) for name in _NAMES)
    clauses, lines = [], []
    details = transfer(
        source, n, target, destination_branch, masks,
        lambda clause: clauses.append(tuple(clause)),
        lambda item: lines.append(json.dumps(
            item, sort_keys=True, separators=(",", ":"))),
        expected_source_hashes=expected_source_hashes,
        allow_audited_migration=allow_audited_migration)
    after = tuple((name, sha(source / name)) for name in _NAMES)
    if before != after:
        raise ValueError("source mutated while it was independently audited")
    if len(clauses) != len(lines) or len(lines) != details["transferred"]:
        raise ValueError("inconsistent independently certified transfer count")
    return SessionTransfer(
        source_path=source, n=n, target=target,
        destination_branch=destination_branch, masks=tuple(masks),
        entries=tuple(zip(clauses, lines)),
        attested_source_hashes=after, certification=details, _seal=_SEAL)
