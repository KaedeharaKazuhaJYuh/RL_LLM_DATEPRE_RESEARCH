"""Design-phase feasibility scratch (not repo code). Exact expected values."""
import math
import sys
from functools import lru_cache

G = 8
H = 10
RATES = {'healthy': (0.90, 0.08, 0.02), 'localized': (0.45, 0.50, 0.05), 'shared': (0.45, 0.05, 0.50)}
P_CC = 0.5
NREL = (0.1, 1.0, 10.0)
CC_COST_FRAC = 0.002
HORIZON = 6


def histories():
    for a in range(H + 1):
        for b in range(H + 1 - a):
            yield (a, b, H - a - b)


def multinom(h, p):
    a, b, c = h
    return math.factorial(H) / (math.factorial(a) * math.factorial(b) * math.factorial(c)) * p[0] ** a * p[1] ** b * p[2] ** c


def predictive(h):
    w = {m: multinom(h, p) / 3 for m, p in RATES.items()}
    z = sum(w.values())
    return z, tuple(sum(w[m] * RATES[m][k] for m in w) / z for k in range(3))


def latents(pred):
    pn, pl, pg = pred
    out = [(('none',), pn), (('global',), pg)]
    for j in range(G):
        for det in (True, False):
            out.append((('local', j, det), pl / G * (P_CC if det else 1 - P_CC)))
    return out


def obs_cc(l):
    return 'flag' if l[0] == 'local' and l[2] else 'ok'


def obs_spot(l, j):
    return 'mismatch' if l[0] == 'global' or (l[0] == 'local' and l[1] == j) else 'match'


def make_dp(pred, C, V, L):
    lat = latents(pred)
    part = C / G
    ccc = C * CC_COST_FRAC

    @lru_cache(None)
    def value(alive, cc_done, rem):
        tot = sum(lat[i][1] for i in alive)
        if tot <= 0:
            return 0.0
        pc = sum(lat[i][1] for i in alive if lat[i][0][0] == 'none') / tot
        best = max(0.0, pc * V - (1 - pc) * L)
        if rem >= 3:
            best = max(best, V - C)
        elif rem == 2:
            best = max(best, pc * V - C)
        if rem >= 2:
            cands = ([('cc', None)] if not cc_done else []) + [('spot', j) for j in range(G)]
            for kind, j in cands:
                groups = {}
                for i in alive:
                    o = obs_cc(lat[i][0]) if kind == 'cc' else obs_spot(lat[i][0], j)
                    groups.setdefault(o, []).append(i)
                if len(groups) == 1:
                    continue
                v = -(ccc if kind == 'cc' else part)
                for idx in groups.values():
                    p = sum(lat[i][1] for i in idx) / tot
                    v += p * value(frozenset(idx), cc_done or kind == 'cc', rem - 1)
                best = max(best, v)
        return best

    return value(frozenset(range(len(lat))), False, HORIZON)


def rule_value(rule, pred, C, V, L):
    lat = latents(pred)
    part = C / G
    ccc = C * CC_COST_FRAC
    tot = 0.0
    kind, arg = rule
    for l, p in lat:
        cost = 0.0
        if kind == 'escalate':
            u = 0.0
        elif kind == 'stop':
            u = V if l[0] == 'none' else -L
        elif kind == 'full':
            u = V - C
        else:
            flagged = False
            if kind in ('ccspot', 'cc'):
                cost += ccc
                flagged = obs_cc(l) == 'flag'
            k = arg if kind != 'cc' else 0
            j = 0
            while not flagged and j < k:
                cost += part
                flagged = obs_spot(l, j) == 'mismatch'
                j += 1
            u = (V - C - cost) if flagged else ((V if l[0] == 'none' else -L) - cost)
        tot += p * u
    return tot


BASE = [('escalate', 0), ('stop', 0), ('full', 0), ('cc', 0)] + [('spot', k) for k in (1, 2, 3, 4)] + [('ccspot', k) for k in (1, 2, 3)]


def regime(kappa, L, V=1.0):
    hs = list(histories())
    pw = {h: predictive(h) for h in hs}
    zs = sum(z for z, _ in pw.values())
    dp_n, rv_n = {}, {}
    for n in NREL:
        C = kappa * V * n
        dp = 0.0
        rv = {r: 0.0 for r in BASE}
        for h in hs:
            z, pr = pw[h]
            w = z / zs
            dp += w * make_dp(pr, C, V, L)
            for r in BASE:
                rv[r] += w * rule_value(r, pr, C, V, L)
        dp_n[n], rv_n[n] = dp, rv
    dp = sum(dp_n.values()) / 3
    best_plain = max(BASE, key=lambda r: sum(rv_n[n][r] for n in NREL))
    plain = sum(rv_n[n][best_plain] for n in NREL) / 3
    sized = sum(max(rv_n[n].values()) for n in NREL) / 3
    full = sum(rv_n[n][('full', 0)] for n in NREL) / 3
    per_n = {n: round((dp_n[n] - max(rv_n[n].values())) / max(dp_n[n], 1e-9), 3) for n in NREL}
    return dp, (dp - plain) / dp, best_plain, (dp - sized) / dp, (dp - full) / dp, per_n


if __name__ == '__main__':
    for L in (1.0, 3.0):
        for kappa in (0.03, 0.1, 0.3, 1.0):
            dp, rp, bp, rs, rf, pn = regime(kappa, L)
            print(f'L={L} k={kappa} U*={dp:.3f} best_plain={rp:.3f} {bp} best_sized={rs:.3f} full={rf:.3f} per_n={pn}', flush=True)
