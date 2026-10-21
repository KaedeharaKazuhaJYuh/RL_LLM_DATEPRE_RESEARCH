"""Small-sample interval estimates and exact paired tests (numpy + stdlib only).

Every resampling function takes an explicit seed and creates its own generator,
so results are deterministic and independent of call order.
"""
from math import comb, sqrt
from statistics import NormalDist

import numpy as np

Z95 = NormalDist().inv_cdf(0.975)
_CHUNK = 1000

#: Significant decimal digits kept by :func:`round_floats` in emitted artifacts.
QUANTIZE_DIGITS = 12


def round_floats(value, digits=QUANTIZE_DIGITS):
    """Recursively round every float to ``digits`` significant decimal digits.

    Reproducibility measure only. A double carries 15-17 significant digits, so
    dropping to 12 discards the last few bits, where CPython and platform
    libraries legitimately disagree: CPython 3.12 gave builtin ``sum()``
    compensated (Neumaier) accumulation, which shifts float sums such as
    :func:`sign_test_power` by 1-2 ULP relative to 3.11. Quantizing makes the
    emitted JSON/Markdown byte-identical across versions and platforms; it
    changes no count, no ordering and no statistical conclusion.

    Significant digits rather than decimal places: the audit reports exact
    sign-test p-values down to ~1e-29, and rounding those to 12 decimal places
    would print them as ``0.0``, asserting an exact zero the test never
    produced. 12 significant digits keeps every p-value and interval bound
    meaningful while still discarding the unstable low bits.

    Ints, bools, strings and ``None`` pass through unchanged, ``-0.0``
    normalises to ``0.0``, and dict key order is preserved. Sequences become
    lists, matching the JSON form the artifacts are written in.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        rounded = float(f'{value:.{digits}g}')
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: round_floats(item, digits) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [round_floats(item, digits) for item in value]
    return value


def _z(confidence):
    if not 0 < confidence < 1:
        raise ValueError('confidence must be in (0, 1)')
    return NormalDist().inv_cdf(1 - (1 - confidence) / 2)


def _count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + ' must be a non-negative int')
    return value


def wilson_interval(successes, n, confidence=0.95):
    """Wilson score interval for a binomial proportion, clipped to [0, 1]."""
    _count(successes, 'successes')
    _count(n, 'n')
    if n == 0:
        raise ValueError('n must be positive')
    if successes > n:
        raise ValueError('successes exceeds n')
    z = _z(confidence)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z / denom * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def _values(values):
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError('values must be a non-empty 1-D sequence')
    return array


def _interval(estimate, replicates, confidence, seed, n_resamples, method, **extra):
    _z(confidence)
    alpha = 1 - confidence
    low, high = np.quantile(replicates, [alpha / 2, 1 - alpha / 2], method='linear')
    result = {'estimate': float(estimate), 'low': float(low), 'high': float(high)}
    result.update(extra)
    result.update({'n_resamples': n_resamples, 'seed': seed,
                   'confidence': confidence, 'method': method})
    return result


def bootstrap_replicates(values, *, n_resamples=10000, seed=560):
    """Means of iid resamples (with replacement) of ``values``."""
    array = _values(values)
    _count(n_resamples, 'n_resamples')
    rng = np.random.default_rng(seed)
    out = np.empty(n_resamples)
    for start in range(0, n_resamples, _CHUNK):
        size = min(_CHUNK, n_resamples - start)
        idx = rng.integers(0, array.size, size=(size, array.size))
        out[start:start + size] = array[idx].mean(axis=1)
    return out


def bootstrap_ci(values, *, n_resamples=10000, confidence=0.95, seed=560):
    """Percentile bootstrap interval for a mean (a proportion for 0/1 values)."""
    array = _values(values)
    reps = bootstrap_replicates(array, n_resamples=n_resamples, seed=seed)
    return _interval(array.mean(), reps, confidence, seed, n_resamples,
                     'percentile_bootstrap', n=int(array.size))


def _clusters(values, clusters):
    array = _values(values)
    labels = [str(c) for c in clusters]
    if len(labels) != array.size:
        raise ValueError('values and clusters differ in length')
    names = sorted(set(labels))
    if len(names) < 2:
        raise ValueError('cluster bootstrap needs at least two clusters')
    index = {name: i for i, name in enumerate(names)}
    codes = np.array([index[c] for c in labels])
    sums = np.bincount(codes, weights=array, minlength=len(names))
    counts = np.bincount(codes, minlength=len(names)).astype(float)
    return array, sums, counts


def cluster_bootstrap_replicates(values, clusters, *, n_resamples=10000, seed=560):
    """Resample whole clusters with replacement; return pooled means."""
    _, sums, counts = _clusters(values, clusters)
    _count(n_resamples, 'n_resamples')
    rng = np.random.default_rng(seed)
    g = sums.size
    out = np.empty(n_resamples)
    for start in range(0, n_resamples, _CHUNK):
        size = min(_CHUNK, n_resamples - start)
        draw = rng.integers(0, g, size=(size, g))
        out[start:start + size] = sums[draw].sum(axis=1) / counts[draw].sum(axis=1)
    return out


def cluster_bootstrap_ci(values, clusters, *, n_resamples=10000, confidence=0.95, seed=560):
    """Percentile cluster bootstrap for a pooled mean; clusters are sorted first."""
    array, sums, _ = _clusters(values, clusters)
    reps = cluster_bootstrap_replicates(array, clusters, n_resamples=n_resamples, seed=seed)
    return _interval(array.mean(), reps, confidence, seed, n_resamples,
                     'cluster_percentile_bootstrap', n=int(array.size), n_clusters=int(sums.size))


def _bools(values):
    out = list(values)
    if any(type(v) is not bool for v in out):
        raise ValueError('paired outcomes must be bool')
    return out


def paired_counts(a, b):
    a, b = _bools(a), _bools(b)
    if len(a) != len(b):
        raise ValueError('paired sequences differ in length')
    pairs = list(zip(a, b))
    return {'n': len(pairs), 'both': sum(x and y for x, y in pairs),
            'a_only': sum(x and not y for x, y in pairs),
            'b_only': sum(y and not x for x, y in pairs),
            'neither': sum(not x and not y for x, y in pairs)}


def exact_sign_test(n_positive, n_negative):
    """Two-sided exact binomial sign test (p = 0.5); 1.0 when there are no signs."""
    _count(n_positive, 'n_positive')
    _count(n_negative, 'n_negative')
    n = n_positive + n_negative
    if n == 0:
        return 1.0
    k = min(n_positive, n_negative)
    tail = sum(comb(n, i) for i in range(k + 1))
    return min(1.0, 2 * tail / 2 ** n)


def mcnemar_exact(a, b):
    """Exact McNemar test: sign test on the discordant pairs."""
    counts = paired_counts(a, b)
    counts['discordant'] = counts['a_only'] + counts['b_only']
    counts['p_value'] = exact_sign_test(counts['a_only'], counts['b_only'])
    counts['method'] = 'exact_mcnemar_two_sided'
    return counts


def holm_bonferroni(p_values):
    """Holm step-down adjusted p-values, returned in input order."""
    ps = [float(p) for p in p_values]
    if any(not 0 <= p <= 1 for p in ps):
        raise ValueError('p-values must be in [0, 1]')
    m = len(ps)
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda j: ps[j])):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def min_discordant_for_significance(alpha=0.05):
    """Smallest discordant count whose most extreme split reaches two-sided alpha."""
    if not 0 < alpha < 1:
        raise ValueError('alpha must be in (0, 1)')
    n = 1
    while exact_sign_test(n, 0) > alpha:
        n += 1
    return n


def sign_test_power(n_discordant, p_direction, alpha=0.05):
    """Exact power of the two-sided sign test given P(discordant pair favours a)."""
    _count(n_discordant, 'n_discordant')
    if not 0 <= p_direction <= 1:
        raise ValueError('p_direction must be in [0, 1]')
    n = n_discordant
    return float(sum(comb(n, k) * p_direction ** k * (1 - p_direction) ** (n - k)
                     for k in range(n + 1) if exact_sign_test(k, n - k) <= alpha))


def mde_two_proportions(n_per_arm, *, baseline=0.5, alpha=0.05, power=0.80):
    """Normal-approximation minimum detectable difference for two proportions."""
    _count(n_per_arm, 'n_per_arm')
    if n_per_arm == 0:
        raise ValueError('n_per_arm must be positive')
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return z * sqrt(2 * baseline * (1 - baseline) / n_per_arm)
