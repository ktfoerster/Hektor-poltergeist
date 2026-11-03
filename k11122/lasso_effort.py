"""Auditable *observed* per-worker SAT effort, never a proof of UNSAT.

Accumulative solver statistics restart at zero after a worker is replaced;
bounded timeouts may lose unsampled work. Only confirmed monotone differences
within one worker generation, plus fresh first readings, are counted.
"""
KEYS = ("conflicts", "decisions", "propagations", "restarts")


def initialize(progress):
    progress["observed_solver_effort"] = {key: 0 for key in KEYS}
    progress["solver_effort_samples"] = 0
    progress["unsampled_bounded_timeouts"] = 0
    progress["solver_effort_worker_generations"] = 0
    return None


def observe(progress, previous, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid solver response")
    if payload.get("bounded_timeout"):
        progress["unsampled_bounded_timeouts"] += 1
        return None  # cannot trust the previous counters after worker death
    generation = payload.get("worker_generation")
    values = payload.get("solver")
    if type(generation) is not int or generation < 1 or not isinstance(values, dict):
        raise ValueError("solver effort must identify its worker generation")
    for key in KEYS:
        if type(values.get(key)) is not int or values[key] < 0:
            raise ValueError("malformed SAT statistic: " + key)
    current = {key: values[key] for key in KEYS}
    if previous is None or previous[0] != generation:
        if previous is not None and generation <= previous[0]:
            raise ValueError("solver worker generation did not increase")
        deltas = current
        progress["solver_effort_worker_generations"] += 1
    else:
        old = previous[1]
        deltas = {key: current[key] - old[key] for key in KEYS}
        if any(delta < 0 for delta in deltas.values()):
            raise ValueError("solver cumulative counters decreased")
    for key in KEYS:
        progress["observed_solver_effort"][key] += deltas[key]
    progress["solver_effort_samples"] += 1
    return generation, current
