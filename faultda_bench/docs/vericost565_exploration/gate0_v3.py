"""Design-phase feasibility scratch v2 (git-excluded, NOT repo code, NOT evidence).

Exact expected values on an equal-parts abstraction of the VeriCost model:
 - latents: none, global, local(j, cc_visible)
 - cc_check reveals the flagged part of a cc-visible local fault; never flags global
 - spot(j) mismatches iff global or local(j); spot(j) also yields part j's independent total,
   so a 'patch' candidate (report with checked parts replaced) exists after any mismatch
 - full_recompute reveals the class and yields c1 (correct)
 - terminal: stop (report correct?), escalate (0); publish(patch|c1) then stop
Rule families: F (outcome-reactive program rules), F_size (N -> F), F_hist (MAP-mode x N -> F),
F_hist_plus (history x N -> F, informational only).
"""
import itertools
import math
import sys
from functools import lru_cache

G = 8
HORIZON = 6
CC_FRAC = 0.002
NREL = ((0.1, 0.25), (1.0, 0.5), (10.0, 0.25))
MODES = ('A', 'B', 'C')


def setup(H, rates, p_cc):
    hs = [(a, b, H - a - b) for a in range(H + 1) for b in range(H + 1 - a)]
    out = []
    for h in hs:
        w = {}
        for m, p in zip(MODES, rates):
            a, b, c = h
            coef = math.factorial(H) / (math.factorial(a) * math.factorial(b) * math.factorial(c))
            w[m] = coef * p[0] ** a * p[1] ** b * p[2] ** c / 3
        z = sum(w.values())
        pred = tuple(sum(w[m] * rates[i][k] for i, m in enumerate(MODES)) / z for k in range(3))
        best = max(w.values())
        map_mode = min(m for m in MODES if abs(w[m] - best) < 1e-15)
        out.append((h, z, pred, map_mode))
    return out


Q_G = 1.0


def latents(pred, p_cc):
    pn, pl, pg = pred
    lat = [(('none',), pn)]
    if Q_G >= 1.0:
        lat.append((('global', (1 << G) - 1), pg))
    else:
        z = 1 - (1 - Q_G) ** G
        for mask in range(1, 1 << G):
            k = bin(mask).count('1')
            lat.append((('global', mask), pg * Q_G ** k * (1 - Q_G) ** (G - k) / z))
    for j in range(G):
        lat.append((('local', j, True), pl / G * p_cc))
        lat.append((('local', j, False), pl / G * (1 - p_cc)))
    return lat


def obs_cc(l):
    return ('flag', l[1]) if l[0] == 'local' and l[2] else 'ok'


def obs_spot(l, j):
    return 'mis' if (l[0] == 'global' and (l[1] >> j) & 1) or (l[0] == 'local' and l[1] == j) else 'ok'


def patch_ok(l, checked):
    if l[0] == 'global':
        return (l[1] & ~checked) == 0
    return l[0] == 'none' or (l[0] == 'local' and (checked >> l[1]) & 1)


def dp_value(lat, C, L, V=1.0):
    part = C / G
    ccc = C * CC_FRAC

    @lru_cache(None)
    def val(alive, cc_done, checked, mism, rem):
        tot = sum(lat[i][1] for i in alive)
        if tot <= 0:
            return 0.0
        pn = sum(lat[i][1] for i in alive if lat[i][0][0] == 'none') / tot
        best = max(0.0, pn * V - (1 - pn) * L)  # escalate / stop
        if mism and rem >= 2:
            pp = sum(lat[i][1] for i in alive if patch_ok(lat[i][0], checked)) / tot
            best = max(best, pp * V - (1 - pp) * L)
        if rem >= 2:  # full_recompute
            v = -C + pn * V + (1 - pn) * (V if rem >= 3 else 0.0)
            best = max(best, v)
            acts = [] if cc_done else [('cc', None)]
            flagged = {lat[i][0][1] for i in alive if lat[i][0][0] == 'local'} if len(alive) <= G * 2 and all(lat[i][0][0] == 'local' for i in alive) else set()
            unchecked = [j for j in range(G) if not (checked >> j) & 1]
            cand = sorted({j for j in flagged if j in unchecked})
            others = [j for j in unchecked if j not in flagged]
            if others:
                cand.append(others[0])
            acts += [('spot', j) for j in cand]
            for kind, j in acts:
                groups = {}
                for i in alive:
                    o = obs_cc(lat[i][0]) if kind == 'cc' else obs_spot(lat[i][0], j)
                    groups.setdefault(o, []).append(i)
                if len(groups) == 1 and kind == 'cc':
                    continue
                if len(groups) == 1 and 'mis' not in groups:
                    continue  # neither informative nor patch-enabling
                v = -(ccc if kind == 'cc' else part)
                for o, idx in groups.items():
                    p = sum(lat[i][1] for i in idx) / tot
                    nchk = checked | (1 << j) if kind == 'spot' else checked
                    nm = mism or (kind == 'spot' and o == 'mis')
                    v += p * val(frozenset(idx), cc_done or kind == 'cc', nchk, nm, rem - 1)
                best = max(best, v)
        return best

    return val(frozenset(range(len(lat))), False, 0, False, HORIZON)


# ---- fixed rules ------------------------------------------------------------------------------
def make_rules():
    rules = [('escalate_all',), ('never_verify',), ('always_full',)]
    for cc in (False, True):
        for k in range(0, 5):
            if not cc and k == 0:
                continue
            for r_mis in (('full', 'patch', 'confirm', 'confirm_esc', 'escalate') if k else ('none',)):
                for r_flag in (('full', 'patch', 'escalate') if cc else ('none',)):
                    rules.append(('check', cc, k, r_mis, r_flag))
    return rules


RULES = make_rules()


def run_rule(rule, l, C, L, V=1.0):
    part = C / G
    ccc = C * CC_FRAC
    if rule[0] == 'escalate_all':
        return 0.0
    if rule[0] == 'never_verify':
        return V if l[0] == 'none' else -L
    if rule[0] == 'always_full':
        return V - C
    _, cc, k, r_mis, r_flag = rule
    rem, cost, checked = HORIZON, 0.0, 0

    def full():
        if rem >= 3:
            return V - cost - C
        if rem == 2:
            return (V if l[0] == 'none' else 0.0) - cost - C
        return -cost

    if cc:
        rem -= 1
        cost += ccc
        o = obs_cc(l)
        if o != 'ok':
            j = o[1]
            if r_flag == 'full':
                return full()
            if r_flag == 'escalate':
                return -cost
            if rem >= 3:
                return V - cost - part
            return -cost
    order = list(range(G))
    for i in range(k):
        if rem <= 1:
            break
        j = order[i]
        rem -= 1
        cost += part
        checked |= 1 << j
        if obs_spot(l, j) == 'mis':
            if r_mis == 'full':
                return full()
            if r_mis == 'escalate':
                return -cost
            if r_mis == 'patch':
                if rem >= 2:
                    return (V if patch_ok(l, checked) else -L) - cost
                return -cost
            # confirm: spot the next unchecked part
            if rem >= 3:
                m = order[i + 1]
                rem -= 1
                cost += part
                checked |= 1 << m
                if obs_spot(l, m) == 'mis':
                    return full() if r_mis == 'confirm' else -cost
                return (V if patch_ok(l, checked) else -L) - cost
            return full() if r_mis == 'confirm' else -cost
    return (V if l[0] == 'none' else -L) - cost


def regime(H, rates, p_cc, kappa, L):
    hist = setup(H, rates, p_cc)
    zs = sum(z for _, z, _, _ in hist)
    dp = 0.0
    rv = {}  # (h, n) -> {rule: value}
    for h, z, pred, mm in hist:
        lat = latents(pred, p_cc)
        for n, wn in NREL:
            C = kappa * n
            w = z / zs * wn
            dp += w * dp_value(lat, C, L)
            rv[(h, n)] = {r: w * sum(p * run_rule(r, l, C, L) for l, p in lat) for r in RULES}
    plain = max(sum(rv[k][r] for k in rv) for r in RULES)
    best_plain = max(RULES, key=lambda r: sum(rv[k][r] for k in rv))
    sized = 0.0
    for n, _ in NREL:
        sized += max(sum(rv[(h, n)][r] for h, *_ in hist) for r in RULES)
    hcell = 0.0
    for m in MODES:
        for n, _ in NREL:
            ks = [(h, n) for h, _, _, mm in hist if mm == m]
            if ks:
                hcell += max(sum(rv[k][r] for k in ks) for r in RULES)
    hplus = sum(max(rv[k].values()) for k in rv)
    full = sum(rv[k][('always_full',)] for k in rv)
    reg = lambda u: (dp - u) / dp
    return dict(U=dp, plain=reg(plain), best_plain=best_plain, size=reg(sized), hist=reg(hcell),
                hplus=reg(hplus), full=reg(full))


BASE_RATES = ((0.90, 0.08, 0.02), (0.45, 0.50, 0.05), (0.45, 0.05, 0.50))

if __name__ == '__main__':
    import json
    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    globals()["Q_G"] = cfg.get("q_g", 1.0)
    H = cfg.get('H', 10)
    rates = tuple(tuple(r) for r in cfg.get('rates', BASE_RATES))
    p_cc = cfg.get('p_cc', 0.5)
    for L in cfg.get('L', (1.0, 3.0)):
        for kappa in cfg.get('kappa', (0.03, 0.1, 0.3, 1.0)):
            r = regime(H, rates, p_cc, kappa, L)
            print(f"H={H} L={L} k={kappa} U*={r['U']:.3f} plain={r['plain']:.3f} size={r['size']:.3f} "
                  f"hist={r['hist']:.3f} hplus={r['hplus']:.3f} full={r['full']:.3f} {r['best_plain']}", flush=True)
