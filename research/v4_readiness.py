"""Read-only V4 readiness check; never reads or prints secret values."""
import argparse
import json
import os
from pathlib import Path
from research.io import ROOT, write_json
from agent.deepseek_config import credential_present


def check():
    protocol_path = ROOT / 'tasks/v4/protocol.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    required = {'primary_metric', 'required_metrics', 'split_unit', 'execution_requirements'}
    provider = 'deepseek' if credential_present() else None
    return {
        'version': protocol['version'],
        'protocol_complete': not (required - set(protocol)),
        'api_provider_configured': provider,
        'live_api_ready': provider is not None,
        'connectivity_verified': False,
        'provider_selected': 'deepseek',
        'test_set_created': False,
        'test_set_sealed': False,
        'next_gate': 'configure_api_credentials' if provider is None else 'implement_isolated_v4_environment'
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out')
    args = parser.parse_args()
    result = check()
    if args.out:
        write_json(Path(args.out), result)
    print(json.dumps(result, indent=2))
