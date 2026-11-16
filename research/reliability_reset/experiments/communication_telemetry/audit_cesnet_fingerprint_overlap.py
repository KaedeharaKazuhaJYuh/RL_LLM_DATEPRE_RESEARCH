"""Count matching flow fingerprints across two ISO weeks without exporting identifiers."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import tables

FIELDS = ('SRC_IP', 'DST_IP', 'DST_PORT', 'PROTOCOL', 'TIME_FIRST', 'TIME_LAST',
          'DURATION', 'BYTES', 'BYTES_REV', 'PACKETS', 'PACKETS_REV', 'PPI', 'PPI_LEN')
EXPECTED = '340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816'
parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
args = parser.parse_args()
digest = hashlib.sha256()
with args.archive.open('rb') as stream:
    while block := stream.read(8 * 1024 * 1024):
        digest.update(block)
if digest.hexdigest() != EXPECTED:
    raise ValueError('unexpected archive hash')
variants = {'with_time': FIELDS, 'without_time': tuple(f for f in FIELDS if f not in ('TIME_FIRST', 'TIME_LAST'))}
counts = {name: {14: Counter(), 15: Counter()} for name in variants}
with tables.open_file(args.archive) as archive:
    for table in archive.list_nodes('/flows', classname='Table'):
        day = date.fromisoformat(f'{table.name[1:5]}-{table.name[5:7]}-{table.name[7:9]}')
        iso = day.isocalendar()
        if iso.year != 2022 or iso.week not in (14, 15):
            continue
        for start in range(0, table.nrows, 25000):
            for row in table.read(start, min(start + 25000, table.nrows)):
                for name, fields in variants.items():
                    fingerprint = hashlib.sha256()
                    for field in fields:
                        value = row[field].tobytes()
                        fingerprint.update(len(value).to_bytes(4, 'little'))
                        fingerprint.update(value)
                    counts[name][iso.week][fingerprint.digest()] += 1
result = {'archive_sha256': EXPECTED, 'weeks': [14, 15], 'variants': {},
          'scope': 'Candidate matches on selected fields only; timestamps are rounded and source port absent. No fingerprints or identifiers exported.'}
for name, fields in variants.items():
    groups = counts[name]
    common = groups[14].keys() & groups[15].keys()
    result['variants'][name] = {'fields': fields,
        'rows': {str(k): sum(v.values()) for k, v in groups.items()},
        'unique_fingerprints': {str(k): len(v) for k, v in groups.items()},
        'within_week_duplicate_rows': {str(k): sum(v.values()) - len(v) for k, v in groups.items()},
        'shared_fingerprints': len(common),
        'rows_in_shared_fingerprints': {str(k): sum(groups[k][x] for x in common) for k in groups}}
output = Path(__file__).with_name('CESNET_XS_FINGERPRINT_OVERLAP_W14_W15_2026_11_10.json')
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
