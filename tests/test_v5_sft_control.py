import json
import unittest

from research.io import ROOT
from research.v5_sft_control_export import scheduled_groups


class SFTControlScheduleTests(unittest.TestCase):
    def test_schedule_uses_training_sources_and_alternates_faults(self):
        train = ROOT / 'tasks/v5/beta_curriculum_v1'
        confirm = ROOT / 'tasks/v5/beta_confirmation_v1'
        tasks = json.loads((train / 'tasks.json').read_text(encoding='utf-8'))
        confirm_sources = {row['source_id'] for row in json.loads(
            (confirm / 'tasks.json').read_text(encoding='utf-8'))}
        for seed in (20260921, 20260922, 20260923):
            with self.subTest(seed=seed):
                groups = scheduled_groups(tasks, seed)
                self.assertEqual(len(groups), 16)
                self.assertEqual([fault for _, fault in groups],
                                 [bool(index % 2) for index in range(16)])
                self.assertFalse({task['source_id'] for task, _ in groups} &
                                 confirm_sources)


if __name__ == '__main__':
    unittest.main()
