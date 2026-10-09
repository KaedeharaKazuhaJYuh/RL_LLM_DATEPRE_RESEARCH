"""Deterministic development probe. No LLM scores and no final-test sources."""
import json
import tempfile
from pathlib import Path

from faultda_bench import PROTOCOL_VERSION
from faultda_bench.baselines import abstain_all, blind_retry, recovery_rule
from faultda_bench.environment import MODES, ReportEnv
from faultda_bench.metrics import aggregate
from research.io import ROOT, digest, write_json

SOURCES = [('uci_auto_mpg', ROOT/'tasks/v5/recovery_beta1/data/auto_mpg.csv', 'mpg'),
           ('uci_glass', ROOT/'tasks/v5/recovery_beta1/data/glass.csv', 'Si')]
SCENARIOS = [{'name': mode, 'mode': mode} for mode in MODES] + [
    {'name': 'query_failed_once', 'mode': 'after_commit', 'query_behavior': 'fail_once'},
    {'name': 'opaque_before', 'mode': 'before_commit', 'query_behavior': 'indeterminate', 'artifact_access': 'unavailable'},
    {'name': 'opaque_after', 'mode': 'after_commit', 'query_behavior': 'indeterminate', 'artifact_access': 'unavailable'}]


def execute(policy, env):
    observation = env.observation()
    while env.terminal is None:
        pending = observation['pending_operation']
        action = policy(observation)
        observation = env.step(action, pending['operation_id'], pending['column'])
    return env.evaluator_record()


def main():
    records = []
    policies = {'rule': recovery_rule, 'blind_retry': blind_retry, 'abstain_all': abstain_all}
    with tempfile.TemporaryDirectory(prefix='faultda_p0_', dir=ROOT/'work') as folder:
        for source_id, source, column in SOURCES:
            for dedup in (False, True):
                for config in SCENARIOS:
                    for name, policy in policies.items():
                        options = {k: v for k, v in config.items() if k != 'name'}
                        env = ReportEnv(source, column, Path(folder)/f'{source_id}_{dedup}_{config["name"]}_{name}',
                                        deduplicate=dedup, **options)
                        records.append({'source_id': source_id, 'split': 'seen_development',
                                        'intent_id': 'publish_numeric_report_record',
                                        'scenario': config['name'], 'policy': name, 'deduplication': dedup,
                                        'param_mode': 'controlled_binding', **execute(policy, env)})
    groups = {}
    for name in policies:
        for dedup in (False, True):
            key = f'{name}:dedup={dedup}'
            rows = [r for r in records if r['policy'] == name and r['deduplication'] == dedup]
            groups[key] = aggregate(rows)
    result = {'protocol_version': PROTOCOL_VERSION, 'status': 'development_probe_not_alpha1_or_llm_evidence',
              'sources': [{'source_id': sid, 'path': path.relative_to(ROOT).as_posix(),
                           'sha256': digest(path), 'used_in_prior_v1_v5': True,
                           'license_manifest': 'tasks/v5/recovery_beta1/manifest.json'} for sid, path, _ in SOURCES],
              'base_intents': 1, 'source_task_clusters': 2, 'episodes': len(records),
              'v5_base_commit': '5fa33c48e5bf9f5e6afa03a22eb2634c397b21d2',
              'implementation_sha256': {name: digest(ROOT/'faultda_bench'/name) for name in (
                  'environment.py', 'verifier.py', 'metrics.py', 'baselines.py', 'probe.py')},
              'scenarios': SCENARIOS,
              'models_evaluated': [], 'summary': groups, 'records': records}
    path = ROOT/'faultda_bench/reports/p0_probe.json'
    write_json(path, result)
    print(json.dumps({k: {m: v[m] for m in ('VTSR', 'SFRR', 'USER', 'SAR')}
                      for k, v in groups.items()}, indent=2))


if __name__ == '__main__':
    main()
