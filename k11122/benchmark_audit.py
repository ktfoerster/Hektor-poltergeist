"""Measure one independent audit in a fresh process; does not invoke a solver.

Run this command separately for each old/new audit module and repetition.
Peak RSS is process-wide (Linux KiB); it includes interpreter/module overhead.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import resource
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--auditor', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('measured_auditor', a.auditor)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = time.monotonic()
    result = module.audit(a.bundle)
    elapsed = time.monotonic() - before
    print(json.dumps(dict(result=result, audit_seconds=elapsed,
                         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                         auditor_sha256=hashlib.sha256(a.auditor.read_bytes()).hexdigest(),
                         python=sys.version, platform=platform.platform()), indent=2))


if __name__ == '__main__':
    main()
