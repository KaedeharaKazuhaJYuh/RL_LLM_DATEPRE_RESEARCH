"""Small opt-in wall-clock profiler for V4 experiment phases."""
from contextlib import contextmanager, nullcontext
import time

from research.io import write_json


class StageProfile:
    def __init__(self, synchronize=None):
        self.started = time.perf_counter()
        self.stages = {}
        self.synchronize = synchronize

    @contextmanager
    def measure(self, name):
        if self.synchronize is not None:
            self.synchronize()
        start = time.perf_counter()
        try:
            yield
        finally:
            if self.synchronize is not None:
                self.synchronize()
            row = self.stages.setdefault(name, {'calls': 0, 'seconds': 0.0})
            row['calls'] += 1
            row['seconds'] += time.perf_counter() - start

    def write(self, path, *, operation, metadata=None):
        wall = time.perf_counter() - self.started
        write_json(path, {'schema_version': 'v4-stage-profile-1',
                          'operation': operation, 'wall_seconds': wall,
                          'device_synchronized': self.synchronize is not None,
                          'stages': {name: {'calls': row['calls'],
                                            'seconds': row['seconds'],
                                            'mean_ms': 1000 * row['seconds'] / row['calls']}
                                     for name, row in sorted(self.stages.items())},
                          'metadata': metadata or {}})


def scope(profile, name):
    return profile.measure(name) if profile is not None else nullcontext()
