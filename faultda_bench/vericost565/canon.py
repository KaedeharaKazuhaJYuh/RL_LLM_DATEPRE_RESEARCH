"""The single serialization boundary: 12-significant-digit floats, write-once artifacts."""
import hashlib
import json
import math

from ..clarity.tasks import write_json

QUANTIZE_DIGITS = 12


def canon(value, digits=QUANTIZE_DIGITS):
    """Rewrite every float at `digits` significant digits; -0.0 becomes 0.0; others untouched."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        quantized = float(f'{value:.{digits}g}')
        return 0.0 if quantized == 0 else quantized
    if isinstance(value, dict):
        return {key: canon(item, digits) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canon(item, digits) for item in value]
    raise TypeError('artifact values must be JSON scalars, lists or dicts: ' + type(value).__name__)


def argmax_first(items):
    """Argmax over (label, value) pairs at round(value, 12); the earliest-listed wins a tie."""
    best = None
    for label, value in items:
        score = round(float(value), QUANTIZE_DIGITS)
        if best is None or score > best[1]:
            best = (label, score)
    if best is None:
        raise ValueError('argmax over an empty candidate list')
    return best[0]


def fsum_(values):
    """Compensated float summation; the only accumulator for float sums in this package."""
    return math.fsum(values)


def dumps(data):
    """Artifact text: exactly the bytes clarity.tasks.write_json writes for the same data."""
    return json.dumps(canon(data), ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def compact(data):
    """Compact canonical text for byte metering, transcripts and hashes; never an artifact."""
    return json.dumps(canon(data), ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def sha_json(data):
    """sha256 of the artifact text, so it equals the sha256 of the written file."""
    return hashlib.sha256(dumps(data).encode()).hexdigest()


def write_json_once(path, data):
    """Write an artifact exactly once; clarity.tasks.write_json opens 'xb' and never overwrites."""
    write_json(path, canon(data))
    return sha_json(data)
