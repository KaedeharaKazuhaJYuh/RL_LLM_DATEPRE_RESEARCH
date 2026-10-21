"""Cross-version determinism: the same bytes under CPython 3.11 and 3.12 (plan item 20)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from faultda_bench.semantic.tasks import REPO
from faultda_bench.vericost565 import analysis, costs, instances, policies, witness
from faultda_bench.vericost565.canon import canon, dumps, sha_json

PY312 = Path('/root/.pyenv/versions/3.12.13/bin/python3.12')
EPISODES = 5000
# The child recomputes the same three digests from this module; numpy is never imported on this
# path, so the 3.12 interpreter (which has no numpy and cannot install it offline) can run it.
CHILD = ('import sys\nsys.path.insert(0, %r)\nimport json\n'
         'from test_faultda_vericost565_determinism import digests\n'
         'print(json.dumps(digests()))\n')


def hand_values():
    """The statistics hand-value set of plan item 18, as one canonical block."""
    return {'signflip': [analysis.signflip_p([1, 2, 3, 4]), analysis.signflip_p([3, -1, 2]),
                         analysis.signflip_p([0, 0]),
                         analysis.signflip_p([1] * 5 + [0] * 10),
                         analysis.signflip_p([0.2] * 6 + [0] * 9),
                         analysis.signflip_p([0.25 - 0.1] * 6)],
            'mcnemar': [analysis.mcnemar_exact(2, 8), analysis.mcnemar_exact(0, 6),
                        analysis.mcnemar_exact(5, 5), analysis.mcnemar_exact(1, 12)],
            'wilson': [list(analysis.wilson(8, 12)), list(analysis.wilson(0, 16)),
                       list(analysis.wilson(18, 18))],
            'holm': [analysis.holm([0.01, 0.04, 0.03]), analysis.holm([0.001, 0.2, 0.04])],
            'icc': [analysis.icc_anova([[1, 1, 1, 1], [0, 0, 0, 0]]),
                    analysis.icc_anova([[1, 0, 1, 0], [1, 0, 1, 0]])],
            'power': analysis.dz_mde(4, 0.05, 0.8, 0.595368090067, analysis.DZ_FORMULA),
            'bootstrap': analysis.cluster_bootstrap([(0.3, 1.0), (-0.1, 2.0), (0.8, 1.5),
                                                     (-0.4, 0.5)], 'ratio', 1000, 5652026),
            'logistic': analysis.logistic_slope([0, 1, 2, 3, 4, 5], [0, 0, 0, 1, 1, 1])}


def profiles():
    return sorted([item for item in instances.build_profiles() if item['kind'] == 'synthetic'],
                  key=lambda item: item['profile_id'])[:2]


def digests():
    return {'fixture': sha_json(witness.fixture(1)),
            'q': sha_json(policies.train_q(profiles(), costs.PRIMARY, EPISODES)),
            'hand': sha_json(hand_values())}


class DeterminismTests(unittest.TestCase):
    def test_the_reduced_witness_run_is_byte_identical_to_the_committed_fixture(self):
        self.assertEqual(dumps(witness.fixture(1)),
                         witness.FIXTURE.read_text(encoding='utf-8'))

    def test_the_reduced_q_training_repeats_byte_for_byte(self):
        first = policies.train_q(profiles(), costs.PRIMARY, EPISODES)
        again = policies.train_q(profiles(), costs.PRIMARY, EPISODES)
        self.assertEqual(dumps(first), dumps(again))
        self.assertEqual(first['stats']['episodes'], EPISODES)
        self.assertGreater(first['stats']['states'], 0)

    def test_the_statistics_hand_values_hold_under_this_interpreter(self):
        values = canon(hand_values())
        self.assertEqual(values['signflip'], [0.0625, 0.25, 1.0, 0.03125, 0.015625, 0.015625])
        self.assertEqual(values['mcnemar'], [0.109375, 0.03125, 1.0, 0.00341796875])
        self.assertEqual(values['wilson'][0], [0.390622088873, 0.861879908909])
        self.assertEqual(values['holm'], [[0.03, 0.06, 0.06], [0.003, 0.2, 0.08]])
        self.assertEqual(values['icc'], [1.0, 0])
        self.assertEqual(values['power']['dz'], 1.66591787358)

    @unittest.skipUnless(PY312.exists(), 'the local 3.12 interpreter is not installed')
    def test_the_3_12_interpreter_produces_the_same_digests(self):
        here = digests()
        done = subprocess.run((str(PY312), '-c', CHILD % str(REPO / 'tests')),
                              capture_output=True, text=True, cwd=str(REPO),
                              env=dict(os.environ, PYTHONPATH='.'))
        self.assertEqual(done.returncode, 0, done.stderr)
        there = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(there, here)
        self.assertNotIn('numpy', done.stderr)


if __name__ == '__main__':
    unittest.main()
