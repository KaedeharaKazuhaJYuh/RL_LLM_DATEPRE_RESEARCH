"""Fixed-commit standalone evidence profile for the focused review."""
import argparse
import json
from pathlib import Path
from . import VERSION
from ..review520.bundle import build


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--commit',required=True);cli.add_argument('--output',type=Path,required=True);a=cli.parse_args()
    print(json.dumps(build(a.commit,a.output,version=VERSION,
        catalog_name='faultda_bench/protocols/acceptance_v43.json',
        result_name='faultda_bench/reports/acceptance_v43_results.json',
        audit_module='faultda_bench.review530.audit',archive_date=(2026,10,19)),ensure_ascii=False,indent=2))
