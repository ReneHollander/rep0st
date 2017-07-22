import sys
from collections import namedtuple
from concurrent.futures import wait, FIRST_COMPLETED
from itertools import islice

import numpy


def batched_pool_runner(f, iterable, pool, batch_size):
    # http://code.activestate.com/lists/python-list/666786/

    it = iter(iterable)
    # Submit the first batch of tasks.
    futures = set(pool.submit(f, x) for x in islice(it, batch_size))
    while futures:
        done, futures = wait(futures, return_when=FIRST_COMPLETED)
        # Replenish submitted tasks up to the number that completed.
        futures.update(pool.submit(f, x) for x in islice(it, len(done)))
        yield from done


class RedirectStdStreams(object):
    def __init__(self, stdout=None, stderr=None):
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


QueueItem = namedtuple('QueueItem', ['priority', 'value'])


class SimplePriorityQueue():
    def __init__(self, max):
        self.max = max
        self.highest = sys.maxsize
        self.list = []

    def search(self, priority):
        lo = 0
        hi = len(self.list)
        while lo < hi:
            mid = (lo + hi) // 2
            if priority < self.list[mid].priority:
                hi = mid
            else:
                lo = mid + 1
        return lo

    def add(self, priority, value):
        if priority < self.highest or len(self.list) < self.max:
            self.list.insert(self.search(priority), QueueItem(priority, value))
        if len(self.list) > self.max:
            self.list.pop()
        self.highest = self.list[-1].priority

    def __iter__(self):
        return self.list.__iter__()

    def __str__(self):
        return self.list.__str__()

    def __repr__(self):
        return self.list.__repr__()

    def get(self, item):
        return self.list[item]

    def __getitem__(self, item):
        return self.list[item]


def batch(n, i):
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))


def dist(x, y):
    return numpy.sqrt(numpy.max(numpy.sum((x - y) ** 2), 0))
