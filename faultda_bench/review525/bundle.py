"""Reuse the fixed-commit bundle validator with this version's explicit profile."""
import argparse
import json
from pathlib import Path
from . import VERSION
from ..review520.bundle import build


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--commit',required=True)
    cli.add_argument('--output',type=Path,required=True); args = cli.parse_args()
    result = build(args.commit,args.output,version=VERSION,
                   catalog_name='faultda_bench/protocols/acceptance_v42.json',
                   result_name='faultda_bench/reports/acceptance_v42_results.json',
                   audit_module='faultda_bench.review525.audit',archive_date=(2026,10,19))
    print(json.dumps(result,ensure_ascii=False,indent=2))
