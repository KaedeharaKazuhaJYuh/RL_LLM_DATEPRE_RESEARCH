"""Reading of the 0.5.66 price-ladder evidence; no provider path and no network use.

This package does not recompute anything. It loads the committed 0.5.66 artifacts and
reproduces the three quantities the release report claims: the regret ladder across
prices, whether any learned arm closes the gap at the only regime with headroom, and the
price elasticity of raw checking volume.
"""
import json
import math
from pathlib import Path

VERSION = '0.5.66-dev'

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / 'reports/vericost566/dev_seen_all_regimes_summary.json'
DETAIL = ROOT / 'reports/vericost566/dev_seen_all_regimes.json'
RELEASE = ROOT / 'reports/RELEASE_0566.md'

LEARNED_ARMS = ('q_only', 'thompson', 'linucb')
FIXED_ARMS = ('bf', 'F', 'F_size', 'F_hist', 'F_hist_plus')


def load(path=None):
    """The committed summary table, unmodified."""
    return json.loads(Path(path or SUMMARY).read_text(encoding='utf-8'))


def detail(path=None):
    """The full per-(profile, regime, arm) expectations behind the summary."""
    return json.loads(Path(path or DETAIL).read_text(encoding='utf-8'))


def rows(data=None):
    """One row per regime, in the pre-registered regime order."""
    return (data or load())['table']


def regret(data=None):
    """{regime_id: {arm: normalized regret}}, as committed."""
    return {row['regime_id']: {name: block['regret_norm'] for name, block in row['arms'].items()}
            for row in rows(data)}


def ladder(data=None):
    """The best-fixed-rule regret at every price; the quantity 0.5.65 reported as one number."""
    return [(row['regime_id'], row['arms']['bf']['regret_norm']) for row in rows(data)]


def headroom_ratio(data=None):
    """Largest over smallest best-fixed regret. 0.5.66 reports roughly 300 for dev_seen."""
    values = [value for _, value in ladder(data)]
    return max(values) / min(values)


def elasticity(arm, loss, low='k0.10', high='k1.00', data=None):
    """Elasticity of raw checking volume w.r.t. kappa between two prices, at fixed L.

    Raw checking volume is `spent_units / kappa`, i.e. billed bytes in reference units;
    `spent_units` already carries the price, so dividing by kappa removes it.
    """
    index = {row['regime_id']: row for row in rows(data)}
    lo, hi = index['%s_L%d' % (low, loss)], index['%s_L%d' % (high, loss)]
    return math.log(hi['arms'][arm]['raw_check_volume'] / lo['arms'][arm]['raw_check_volume']) \
        / math.log(hi['kappa'] / lo['kappa'])


def closes_gap(regime_id, data=None):
    """Arms whose regret is strictly below the best fixed rule at one regime."""
    block = regret(data)[regime_id]
    best = block['bf']
    return sorted(name for name, value in block.items()
                  if name != 'bf' and value < best - 1e-12)


def main():
    data = load()
    print('%s  instance_set=%s profiles=%d regimes=%d arms=%d api_calls=%d'
          % (data['version'], data['instance_set'], data['profiles'], data['regimes'],
             data['arms'], data['api_calls']))
    print()
    print('regime        bf       thompson  linucb    q_only    F_hist_plus')
    for row in rows(data):
        arms = row['arms']
        print('%-12s  %.4f   %.4f    %.4f    %.4f    %.4f'
              % (row['regime_id'], arms['bf']['regret_norm'], arms['thompson']['regret_norm'],
                 arms['linucb']['regret_norm'], arms['q_only']['regret_norm'],
                 arms['F_hist_plus']['regret_norm']))
    print()
    print('headroom ratio (max/min best-fixed regret): %.0f' % headroom_ratio(data))
    for arm in ('bf',) + LEARNED_ARMS:
        print('elasticity %-9s L=1 %.2f   L=3 %.2f'
              % (arm, elasticity(arm, 1, data=data), elasticity(arm, 3, data=data)))
    print()
    print('arms below bf at k1.00_L3:', closes_gap('k1.00_L3', data) or 'none')
    print('arms below bf at k0.30_L3:', closes_gap('k0.30_L3', data) or 'none')


if __name__ == '__main__':
    main()
