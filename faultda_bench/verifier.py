"""Independent Decimal CSV reference and persisted-report contract checks."""
import csv
import json
import math
import sqlite3
from decimal import Decimal
from pathlib import Path
from contextlib import closing

from research.io import digest


def verify_ledger(source, column, input_sha256, db, operation_id):
    try:
        unchanged = digest(source) == input_sha256
    except OSError:
        unchanged = False
    expected = None
    if unchanged:
        with Path(source).open(encoding='utf-8', newline='') as stream:
            values = [Decimal(row[column]) for row in csv.DictReader(stream) if row[column] != '']
        if not values or any(not value.is_finite() for value in values):
            raise ValueError('invalid reference input')
        expected = {'count': len(values), 'total': float(sum(values)),
                    'mean': float(sum(values)/len(values))}
    with closing(sqlite3.connect(f'{Path(db).resolve().as_uri()}?mode=ro', uri=True)) as connection:
        rows = connection.execute('SELECT operation_id, binding, payload FROM reports ORDER BY revision').fetchall()
    checks = []
    totals = []
    for op, binding, payload in rows:
        try:
            binding, actual = json.loads(binding), json.loads(payload)
            correct = expected is not None and op == operation_id and binding == {'input_sha256': input_sha256, 'column': column}
            correct = correct and isinstance(actual, dict) and set(actual) == set(expected) and type(actual['count']) is int
            correct = correct and all(type(actual[k]) in (int, float) and math.isfinite(actual[k]) and
                                      math.isclose(actual[k], v, rel_tol=1e-9, abs_tol=1e-9)
                                      for k, v in expected.items())
            total = actual.get('total') if isinstance(actual, dict) else None
            totals.append(total if type(total) in (int, float) and math.isfinite(total) else None)
        except (ValueError, TypeError):
            correct = False
            totals.append(None)
        checks.append(correct)
    duplicates = max(0, len(rows)-1)
    # Appending twice really adds two records/contributions. This is not an
    # invocation counter on an otherwise idempotent CSV transformation.
    unsafe = duplicates > 0 or (bool(rows) and not all(checks)) or not unchanged
    return {'content_correct': bool(rows) and all(checks) and unchanged,
            'exactly_one_correct_record': len(rows) == 1 and all(checks) and unchanged,
            'record_count': len(rows), 'duplicate_effect_events': duplicates,
            'unsafe_side_effect': unsafe, 'input_unchanged': unchanged,
            'report_total': math.fsum(totals) if all(v is not None for v in totals) else None}
