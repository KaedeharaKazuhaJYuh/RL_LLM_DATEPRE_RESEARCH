"""Run a fixed majority-class control on W15; this is not a trained model."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .cesnet_prequential import run_week

EXPECTED = '340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816'
HERE = Path(__file__).parent
INPUT_FILES = {
    'CESNET_TLS_YEAR22_XS_DATE_APP_COUNTS_2026_11_10.csv': 'bd5331a573168e593ed6a5608212cbd409baa359af213c5cc4ed6ae8006493c9',
    'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv': '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d',
}
parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
parser.add_argument('--prediction-path', required=True, type=Path)
parser.add_argument('--summary-path', required=True, type=Path)
args = parser.parse_args()
digest = hashlib.sha256()
with args.archive.open('rb') as stream:
    while block := stream.read(8 * 1024 * 1024):
        digest.update(block)
if digest.hexdigest() != EXPECTED:
    raise ValueError('archive SHA-256 does not match the fixed XS census')
for filename, expected_hash in INPUT_FILES.items():
    canonical_bytes = (HERE / filename).read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(canonical_bytes).hexdigest() != expected_hash:
        raise ValueError(f'fixed input checksum mismatch: {filename}')

counts = Counter()
with (HERE / 'CESNET_TLS_YEAR22_XS_DATE_APP_COUNTS_2026_11_10.csv').open(encoding='utf-8', newline='') as stream:
    for row in csv.DictReader(stream):
        if int(row['iso_year']) == 2022 and 11 <= int(row['iso_week']) <= 14:
            counts[int(row['app_code'])] += int(row['rows'])
counts = Counter({code: count for code, count in counts.items() if count})
classes = np.asarray(sorted(counts), dtype=np.int32)
majority = min(code for code, count in counts.items() if count == max(counts.values()))
with (HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv').open(encoding='utf-8', newline='') as stream:
    dates = [row['date'] for row in csv.DictReader(stream) if row['iso_year'] == '2022' and row['iso_week'] == '15']

score, released = run_week(args.archive, dates,
                           lambda batch: np.full(len(batch.row_indices), majority, dtype=np.int32),
                           classes, 1000, 20261112, args.prediction_path)
result = {'experiment': 'W15 fixed initialization-majority engineering control',
          'not_a_model_training_result': True, 'dataset_sha256': EXPECTED,
          'full_initialization_labels_used_for_majority_and_vocabulary': True,
          'fixed_input_lf_normalized_hashes': INPUT_FILES,
          'initialization_weeks': [11, 12, 13, 14], 'evaluation_week': 15,
          'dates': dates, 'constant_app_code': majority, 'initialization_flows': sum(counts.values()),
          'numpy_version': np.__version__, 'score': score,
          'sampled_distinct_app_codes': len({label for _, _, label in released}),
          'note': 'Unbudgeted initialization-label oracle; not a fair budget-matched model baseline. Prediction file and released row-level labels stay local; no model update or novelty conclusion.'}
args.summary_path.parent.mkdir(parents=True, exist_ok=True)
args.summary_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
