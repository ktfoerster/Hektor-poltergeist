"""Deterministic CNF export and conservative independent RUP certification."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def export(output, target, masks, branch=-1, n=7):
    from sat_search import BooleanEncoding, partition
    class StreamEncoding(BooleanEncoding):
        def add_clause(self, clause):
            clause = list(clause)
            if not clause:
                raise ValueError('unexpected empty encoder clause')
            data = (' '.join(map(str, clause)) + ' 0\n').encode()
            body.write(data)
            self.clause_count += 1
            self.fingerprint.update(data)
    output = pathlib.Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryFile() as body:
        enc = StreamEncoding(n, target)
        try:
            split = partition(enc, branch)
            for mask in sorted(set(masks)):
                enc.add(mask)
            with (output / 'formula.cnf').open('wb') as f:
                f.write(f'p cnf {enc.top} {enc.clause_count}\n'.encode())
                body.seek(0)
                shutil.copyfileobj(body, f)
            metadata = dict(schema=1, n=n, target=target, partition=split,
                            masks=enc.masks, variables=enc.top, clauses=enc.clause_count,
                            clause_body_sha256=enc.fingerprint.hexdigest(),
                            cnf_sha256=sha(output / 'formula.cnf'),
                            encoder_sha256=sha(pathlib.Path(__file__).with_name('sat_search.py')),
                            exporter_sha256=sha(__file__),
                            scope='finite residual family; branch-specific when partition is present')
            (output / 'selectors.json').write_text(json.dumps([
                [*key, choices] for key, choices in sorted(enc.rows.items())]))
            metadata['selectors_sha256'] = sha(output / 'selectors.json')
            (output / 'export.json').write_text(json.dumps(metadata, indent=2, sort_keys=True))
        finally:
            enc.delete()
    return metadata


def iter_cnf(path):
    """Stream DIMACS and validate the header/count before successful EOF."""
    count, pending, header = 0, [], None
    with pathlib.Path(path).open() as source:
        for line in source:
            fields = line.split()
            if not fields or fields[0] == 'c':
                continue
            if fields[0] == 'p':
                if header is not None or len(fields) != 4 or fields[1] != 'cnf':
                    raise ValueError('invalid header')
                header = tuple(map(int, fields[2:]))
                if min(header) < 0:
                    raise ValueError('negative header count')
                continue
            if header is None:
                raise ValueError('missing header')
            for value in map(int, fields):
                if abs(value) > header[0]:
                    raise ValueError('literal out of bounds')
                if value:
                    pending.append(value)
                else:
                    count += 1
                    yield set(pending)
                    pending = []
    if header is None or pending or count != header[1]:
        raise ValueError('truncated formula')


def read_cnf(path):
    return list(iter_cnf(path))


def rup(clauses, candidate):
    # Independent Boolean unit propagation, no SAT solver library.
    assignment = set(-x for x in candidate)
    if any(-x in assignment for x in assignment):
        return True
    while True:
        changed = False
        for clause in clauses:
            if clause & assignment:
                continue
            remaining = {x for x in clause if -x not in assignment}
            if not remaining:
                return True
            if len(remaining) == 1:
                value = next(iter(remaining))
                if value not in assignment:
                    assignment.add(value)
                    changed = True
        if not changed:
            return False


def check(cnf, proof, engine='watched'):
    initial_cnf, initial_proof = sha(cnf), sha(proof)
    if engine == 'watched':
        from rup_watch import WatchedRUP
        database = WatchedRUP(iter_cnf(cnf))
        propagate, add = database.rup, database.add
    elif engine == 'reference':
        clauses = read_cnf(cnf)
        propagate, add = lambda clause: rup(clauses, clause), clauses.append
    else:
        raise ValueError('unknown checker engine')
    empty = False
    additions = 0
    with pathlib.Path(proof).open() as source:
        for line in source:
            fields = line.split()
            if not fields or fields[0] == 'c':
                continue
            deletion = fields[0] == 'd'
            values = list(map(int, fields[1:] if deletion else fields))
            if not values or values[-1] != 0 or 0 in values[:-1]:
                raise ValueError('invalid proof line')
            if deletion:
                continue  # retain only original/proven clauses: sound
            clause = set(values[:-1])
            if not propagate(clause):
                raise ValueError('addition is not RUP (RAT-only steps are unsupported)')
            add(clause)
            additions += 1
            empty |= not clause
    if not empty:
        raise ValueError('proof has no checked empty clause')
    if initial_cnf != sha(cnf) or initial_proof != sha(proof):
        raise ValueError('input changed during verification')
    result = dict(status='CNF_UNSAT_RUP_VERIFIED', additions=additions,
                  engine=engine, cnf_sha256=initial_cnf, proof_sha256=initial_proof,
                  checker_sha256=sha(__file__))
    if engine == 'watched':
        result['propagator_sha256'] = sha(pathlib.Path(__file__).with_name('rup_watch.py'))
    return result


def solve(cnf, proof):
    from pysat.solvers import Solver
    with Solver(name='glucose3', bootstrap_with=(sorted(c) for c in iter_cnf(cnf)),
                with_proof=True) as solver:
        if solver.solve():
            pathlib.Path(proof).with_name('model.json').write_text(json.dumps(solver.get_model()))
            return 'SAT_FINITE_CNF'
        pathlib.Path(proof).write_text('\n'.join(solver.get_proof()) + '\n')
        return 'UNSAT_UNCERTIFIED'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['export', 'solve', 'check', 'certify'])
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--checkpoint', type=pathlib.Path)
    p.add_argument('--target', type=int, choices=[0, 3])
    p.add_argument('--branch', type=int, choices=[-1, 0, 1], default=-1)
    p.add_argument('--checker', choices=['watched', 'reference'], default='watched')
    p.add_argument('--seconds', type=int, default=60)
    a = p.parse_args()
    if not 1 <= a.seconds <= 3600:
        p.error('seconds must be 1..3600 per phase')
    cnf, proof = a.output / 'formula.cnf', a.output / 'proof.drup'
    if a.mode == 'export':
        from sat_search import load_checkpoint
        if a.target is None or a.checkpoint is None:
            p.error('export requires target and checkpoint')
        export(a.output, a.target, load_checkpoint(a.checkpoint, a.target), a.branch)
    elif a.mode == 'solve':
        print(solve(cnf, proof))
    elif a.mode == 'check':
        print(json.dumps(check(cnf, proof, a.checker), sort_keys=True))
    else:
        # Each child is bounded and subprocess.run kills and joins on timeout.
        result = {'status': 'UNKNOWN', 'cnf_sha256': sha(cnf)}
        (a.output / 'certification.json').write_text(json.dumps(result))
        proof.unlink(missing_ok=True)
        (a.output / 'model.json').unlink(missing_ok=True)
        for phase in ['solve', 'check']:
            try:
                child = subprocess.run([sys.executable, __file__, phase, '--output', str(a.output), '--checker', a.checker],
                                       capture_output=True, text=True, timeout=a.seconds)
                (a.output / (phase + '.log')).write_text(child.stdout + child.stderr)
                if child.returncode:
                    result['reason'] = phase + ' failed; see log'
                    break
                if phase == 'solve' and child.stdout.strip() == 'SAT_FINITE_CNF':
                    result['status'] = 'SAT_FINITE_CNF'
                    break
                if phase == 'check':
                    result = json.loads(child.stdout)
            except subprocess.TimeoutExpired:
                result['reason'] = phase + ' timed out'
                break
        (a.output / 'certification.json').write_text(json.dumps(result, indent=2, sort_keys=True))
        print(json.dumps(result))


if __name__ == '__main__':
    main()
