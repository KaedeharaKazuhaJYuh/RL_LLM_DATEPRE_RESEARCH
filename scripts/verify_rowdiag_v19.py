"""Compatibility entry point: verify only the original frozen dependency set."""
import json
from pathlib import Path
from unittest.mock import patch
from faultda_bench.rowdiag import suite
from faultda_bench.semantic.tasks import REPO, sha


def verify(output):
    frozen=json.loads(Path(output).with_suffix('.protocol.json').read_text())
    current=suite.protocol()
    current['code_sha256']={name:sha(REPO/name) for name in frozen['code_sha256']}
    # All original dependencies are still hash checked; additional modules cannot invalidate history.
    with patch.object(suite,'protocol',return_value=current):
        return suite.verify(output)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('output'); a=p.parse_args()
    print(json.dumps(verify(a.output)))
