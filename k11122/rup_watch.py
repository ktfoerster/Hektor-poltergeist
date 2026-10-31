"""Incremental two-watched-literal RUP propagation; no solver dependency.

Assignments are fresh for each query; watch movements persist. Deletions are
ignored by the caller, so all stored clauses are original or already proved.
"""
from collections import defaultdict, deque


class WatchedRUP:
    def __init__(self, clauses):
        self.clauses = []
        self.watches = defaultdict(list)
        self.units = []
        self.has_empty = False
        for clause in clauses:
            self.add(clause)

    def add(self, clause):
        values = sorted(set(clause))
        if any(-value in values for value in values):
            return  # tautologies impose no propagation obligation
        if not values:
            self.has_empty = True
        elif len(values) == 1:
            self.units.append(values[0])
        else:
            index = len(self.clauses)
            self.clauses.append(values)
            self.watches[values[0]].append(index)
            self.watches[values[1]].append(index)

    def rup(self, candidate):
        if self.has_empty:
            return True
        assigned, queue = set(), deque()

        def enqueue(value):
            if -value in assigned:
                return False
            if value not in assigned:
                assigned.add(value)
                queue.append(value)
            return True

        for value in candidate:
            if not enqueue(-value):
                return True
        for value in self.units:
            if not enqueue(value):
                return True
        while queue:
            false = -queue.popleft()
            watching = self.watches[false]
            i = 0
            while i < len(watching):
                index = watching[i]
                clause = self.clauses[index]
                if clause[0] != false:
                    clause[0], clause[1] = clause[1], clause[0]
                assert clause[0] == false
                other = clause[1]
                if other in assigned:
                    i += 1
                    continue
                replacement = next((j for j in range(2, len(clause))
                                    if -clause[j] not in assigned), None)
                if replacement is not None:
                    clause[0], clause[replacement] = clause[replacement], clause[0]
                    self.watches[clause[0]].append(index)
                    watching[i] = watching[-1]
                    watching.pop()
                    continue
                if not enqueue(other):
                    return True
                i += 1
        return False
