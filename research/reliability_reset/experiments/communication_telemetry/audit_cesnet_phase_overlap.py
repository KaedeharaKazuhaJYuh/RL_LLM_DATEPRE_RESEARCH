"""Compare source identifiers across initialization and development weeks."""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
import numpy as np
import tables

parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
args = parser.parse_args()
digest = hashlib.sha256()
with args.archive.open('rb') as stream:
    while block := stream.read(8 * 1024 * 1024):
        digest.update(block)
if digest.hexdigest() != '340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816':
    raise ValueError('archive hash mismatch')
groups = {'initialization': [], 'development': []}
with tables.open_file(args.archive) as archive:
    for table in archive.list_nodes('/flows', classname='Table'):
        day = date.fromisoformat(f'{table.name[1:5]}-{table.name[5:7]}-{table.name[7:9]}')
        iso = day.isocalendar()
        if iso.year == 2022 and 11 <= iso.week <= 18:
            phase = 'initialization' if iso.week <= 14 else 'development'
            groups[phase].append(table.read(field='SRC_IP'))
sets = {phase: set(np.concatenate(rows).tolist()) for phase, rows in groups.items()}
shared = len(sets['initialization'] & sets['development'])
result = {'archive_sha256': digest.hexdigest(), 'flows': {k: sum(len(x) for x in v) for k, v in groups.items()},
          'unique_source_strings': {k: len(v) for k, v in sets.items()}, 'shared_source_strings': shared,
          'fraction_development_sources_seen_in_initialization': shared / len(sets['development']),
          'scope': 'Exact equality of pseudonymous source strings, not proof of client identity or duplicated sessions.'}
output = Path(__file__).with_name('CESNET_XS_SOURCE_OVERLAP_PHASES_2026_11_10.json')
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
