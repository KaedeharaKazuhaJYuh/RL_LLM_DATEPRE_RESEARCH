"""The exact DP oracle: the alive-set INV-DP definition and its compact fast path."""
import functools

from . import costs, instances, simulator
from .canon import argmax_first, compact, fsum_
from .environment import VeriCostEnv, transcript

TOL = 1e-9
HORIZON = simulator.HORIZON
CC_NONE, CC_OK = -2, -1
# The active report plus the forbidden-effect floor: (active, cover, floor, duplicate).
NO_PUBLISH = ('report', 0, -1, False)
TERMINAL_ACTIONS = ('escalate', 'stop', 'publish_patch', 'publish_c1')


def mask_of(parts):
    bits = 0
    for part in parts:
        bits |= 1 << part
    return bits


def publish_state(pub, candidate, mode, checked):
    """Fold one publish into the report state; a wrong patch and an append are never undone."""
    active, _, floor, duplicate = pub
    duplicate = duplicate or mode == 'append'
    if candidate == 'c1' or active == 'source':
        return ('source', 0, floor, duplicate)
    return ('patch', checked, checked if floor < 0 else floor, duplicate)


def history_bytes(history):
    """The canonical public transcript of a history, exactly as environment.transcript writes it."""
    return compact([{'action': entry['action'], 'params': entry['params'],
                     'response': entry['response']} for entry in history])


class Oracle:
    """One DP solve over a (profile, history, regime, model); every cache dies with the object."""

    def __init__(self, profile, counts, regime_id, model='rev1', horizon=HORIZON):
        self.profile = profile
        self.parts = len(profile['parts'])
        self.counts = dict(counts)
        self.regime_id = regime_id
        self.model = model
        self.horizon = horizon
        self.loss = costs.regime(regime_id)['L']
        self.latents = simulator.latents(model, self.parts)
        prior = simulator.latent_prior(profile, counts, model)
        self.weights = tuple(prior[latent] for latent in self.latents)
        self.affected = tuple(mask_of(simulator.affected_parts(latent, self.parts))
                              for latent in self.latents)
        self.flags = tuple(simulator.cc_flagged(latent) for latent in self.latents)
        self.cc_cost = costs.cost(profile, regime_id, 'consistency_check')
        self.full_cost = costs.cost(profile, regime_id, 'full_recompute')
        self.spot_cost = tuple(costs.cost(profile, regime_id, 'spot_check', part)
                               for part in range(self.parts))
        self.read_cost = tuple(costs.cost(profile, regime_id, 'read_rows', part)
                               for part in range(self.parts))
        self.root = tuple(range(len(self.latents)))
        self.mass = functools.lru_cache(None)(self._mass)
        self.alive_of = functools.lru_cache(None)(self._alive_of)
        self.general = functools.lru_cache(None)(self._general_value)
        self.compact = functools.lru_cache(None)(self._compact_value)

    # ---- beliefs -------------------------------------------------------------------------------
    def _mass(self, alive):
        return fsum_([self.weights[index] for index in alive])

    def _alive_of(self, cc, checked, mismatch, full):
        """INV-DP (b): the alive set is a pure function of the compact state."""
        out = []
        for index in range(len(self.latents)):
            affected, flag = self.affected[index], self.flags[index]
            if affected & checked != mismatch:
                continue
            if cc == CC_OK and flag:
                continue
            if cc >= 0 and flag != (cc,):
                continue
            if full == 'match' and affected:
                continue
            if full == 'mismatch' and not affected:
                continue
            out.append(index)
        return tuple(out)

    def correct(self, index, pub):
        if pub[0] == 'source':
            return True
        if pub[0] == 'patch':
            return not self.affected[index] & ~pub[1]
        return not self.affected[index]

    def forbidden(self, index, pub):
        return pub[3] or (pub[2] >= 0 and bool(self.affected[index] & ~pub[2]))

    def _end(self, alive, pub, stopped):
        """Ending now: stop scores V or -L per latent, escalate and horizon only the penalty."""
        terms = []
        for index in alive:
            if stopped:
                ok = self.correct(index, pub) and not self.forbidden(index, pub)
                terms.append(self.weights[index] * (costs.V if ok else -self.loss))
            elif self.forbidden(index, pub):
                terms.append(self.weights[index] * -self.loss)
        return fsum_(terms) / self.mass(alive)

    def groups(self, kind, part, alive):
        """Alive latents grouped by the observation of one action, in a fixed key order."""
        groups = {}
        for index in alive:
            if kind == 'cc':
                key = self.flags[index]
            elif kind == 'full':
                key = self.affected[index]
            elif kind == 'full_coarse':
                key = bool(self.affected[index])
            else:
                key = bool(self.affected[index] >> part & 1)
            groups.setdefault(key, []).append(index)
        return [(key, tuple(members)) for key, members in sorted(groups.items())]

    # ---- the general solver: the definition ----------------------------------------------------
    def _general_branch(self, alive, kind, part, cost, checked, cc_done, full, pub, rem):
        total = self.mass(alive)
        terms = [-cost]
        for key, members in self.groups(kind, part, alive):
            next_checked = checked | (1 << part) if kind == 'spot' else checked
            next_full = ('mismatch' if key else 'match') if kind == 'full' else full
            terms.append(self.mass(members) / total
                         * self.general(members, next_checked, cc_done or kind == 'cc',
                                        next_full, pub, rem - 1))
        return fsum_(terms)

    def general_items(self, alive, checked, cc_done, full, pub, rem):
        """Every legal action at a general state, in the pre-registered tie-break order."""
        items = [('escalate', self._end(alive, pub, False)), ('stop', self._end(alive, pub, True))]
        if rem < 2:
            return items
        if self.affected[alive[0]] & checked:
            items.append(('publish_patch',
                          self._end(alive, publish_state(pub, 'patch', 'replace', checked), True)))
        if full != 'none':
            items.append(('publish_c1',
                          self._end(alive, publish_state(pub, 'c1', 'replace', checked), True)))
        if not cc_done:
            items.append(('cc', self._general_branch(alive, 'cc', None, self.cc_cost, checked,
                                                     cc_done, full, pub, rem)))
        for part in range(self.parts):  # no pruning: every unchecked part is a spot candidate
            if not checked >> part & 1:
                items.append((f'spot:{part}',
                              self._general_branch(alive, 'spot', part, self.spot_cost[part],
                                                   checked, cc_done, full, pub, rem)))
        if full == 'none':
            items.append(('full', self._general_branch(alive, 'full', None, self.full_cost, checked,
                                                       cc_done, full, pub, rem)))
        return items

    def _general_value(self, alive, checked, cc_done, full, pub, rem):
        if not alive:
            return 0.0
        if rem <= 0:
            return self._end(alive, pub, False)
        items = self.general_items(alive, checked, cc_done, full, pub, rem)
        chosen = argmax_first(items)
        return next(value for label, value in items if label == chosen)

    def general_root(self):
        return self.general(self.root, 0, False, 'none', NO_PUBLISH, self.horizon)

    # ---- the compact solver: the fast path -----------------------------------------------------
    def successors(self, kind, part, state):
        """The compact successor states of one action, with the alive group reaching each."""
        cc, checked, mismatch, full, rem = state
        alive = self.alive_of(cc, checked, mismatch, full)
        out = []
        for key, members in self.groups('full_coarse' if kind == 'full' else kind, part, alive):
            next_cc, next_checked, next_mismatch, next_full = cc, checked, mismatch, full
            if kind == 'cc':
                next_cc = key[0] if key else CC_OK
            elif kind == 'spot':
                next_checked = checked | (1 << part)
                next_mismatch = mismatch | (1 << part) if key else mismatch
            else:
                next_full = 'mismatch' if key else 'match'
            out.append((members, (next_cc, next_checked, next_mismatch, next_full, rem - 1)))
        return out

    def _compact_branch(self, kind, part, cost, state):
        alive = self.alive_of(*state[:4])
        total = self.mass(alive)
        terms = [-cost]
        for members, child in self.successors(kind, part, state):
            terms.append(self.mass(members) / total * self.compact(*child))
        return fsum_(terms)

    def compact_items(self, cc, checked, mismatch, full, rem):
        """The action table of design 2.5, with no action pruning of any kind."""
        state = (cc, checked, mismatch, full, rem)
        alive = self.alive_of(cc, checked, mismatch, full)
        items = [('escalate', self._end(alive, NO_PUBLISH, False)),
                 ('stop', self._end(alive, NO_PUBLISH, True))]
        if rem < 2:
            return items
        if mismatch:
            items.append(('publish_patch',
                          self._end(alive, publish_state(NO_PUBLISH, 'patch', 'replace', checked),
                                    True)))
        if full != 'none':
            items.append(('publish_c1',
                          self._end(alive, publish_state(NO_PUBLISH, 'c1', 'replace', checked),
                                    True)))
        if cc == CC_NONE:
            items.append(('cc', self._compact_branch('cc', None, self.cc_cost, state)))
        for part in range(self.parts):
            if not checked >> part & 1:
                items.append((f'spot:{part}',
                              self._compact_branch('spot', part, self.spot_cost[part], state)))
        if full == 'none':
            items.append(('full', self._compact_branch('full', None, self.full_cost, state)))
        return items

    def _compact_value(self, cc, checked, mismatch, full, rem):
        alive = self.alive_of(cc, checked, mismatch, full)
        if not alive or rem <= 0:
            return 0.0
        items = self.compact_items(cc, checked, mismatch, full, rem)
        chosen = argmax_first(items)
        return next(value for label, value in items if label == chosen)

    def compact_root(self):
        return self.compact(CC_NONE, 0, 0, 'none', self.horizon)

    def compact_policy(self, state):
        return argmax_first(self.compact_items(*state))

    def onpath(self):
        """Every compact state reached under DP-optimal play, for any alive latent (C3)."""
        root = (CC_NONE, 0, 0, 'none', self.horizon)
        order, seen, queue = [root], {root}, [root]
        while queue:
            state = queue.pop(0)
            if state[4] < 2:
                continue
            chosen = self.compact_policy(state)
            if chosen in TERMINAL_ACTIONS:
                continue
            kind, part = ('spot', int(chosen.split(':')[1])) if chosen.startswith('spot') else (chosen, None)
            for _, child in self.successors(kind, part, state):
                if child not in seen:
                    seen.add(child)
                    order.append(child)
                    queue.append(child)
        return order

    # ---- deviations over the complete action alphabet -------------------------------------------
    def q_value(self, alive, checked, cc_done, full, pub, rem, action):
        """The exact value of any action at a general state, reads and republishes included."""
        if rem <= 0 or not alive:
            raise ValueError('no decision remains')
        kind = action[0]
        if kind == 'escalate':
            return self._end(alive, pub, False)
        if kind == 'stop':
            return self._end(alive, pub, True)
        if kind == 'publish':
            candidate, mode = action[1], action[2]
            available = (full != 'none') if candidate == 'c1' else bool(self.affected[alive[0]] & checked)
            nxt = publish_state(pub, candidate, mode, checked) if available else pub
            return self.general(alive, checked, cc_done, full, nxt, rem - 1)
        if kind == 'cc':
            return self._general_branch(alive, 'cc', None, self.cc_cost, checked, cc_done, full,
                                        pub, rem)
        if kind == 'full':
            return self._general_branch(alive, 'full', None, self.full_cost, checked, cc_done,
                                        full, pub, rem)
        if kind == 'spot':
            part = action[1]
            return self._general_branch(alive, 'spot', part, self.spot_cost[part], checked,
                                        cc_done, full, pub, rem)
        if kind == 'read':
            # A read is priced at the full part scan and credited with the whole affected_j bit,
            # which bounds every truncated or empty page from above (design 2.3 lemma 1).
            part = action[1]
            return self._general_branch(alive, 'read', part, self.read_cost[part], checked,
                                        cc_done, full, pub, rem)
        raise ValueError('unknown action: ' + str(kind))

    # ---- public histories ----------------------------------------------------------------------
    def replay(self, latent, history):
        """The canonical transcript of one latent under the actions of `history`."""
        env = VeriCostEnv(instances.materialize(self.profile, latent), counts=self.counts,
                          regime=self.regime_id)
        for entry in history:
            if env.terminal:
                break
            env.step(entry['action'], entry['params'])
        text = transcript(env)
        env.close()
        return text

    def alive_from_history(self, history):
        """INV-DP (a): the latents whose replayed transcript matches h byte for byte."""
        target = history_bytes(history)
        return tuple(index for index, latent in enumerate(self.latents)
                     if self.replay(latent, history) == target)

    def state_from_history(self, history):
        checked, cc_done, full, pub, ended = 0, False, 'none', NO_PUBLISH, None
        for entry in history:
            action, response = entry['action'], entry['response']
            if not response.get('ok'):
                continue
            if action == 'consistency_check':
                cc_done = True
            elif action == 'spot_check':
                checked |= 1 << response['part']
            elif action == 'full_recompute':
                full = 'mismatch' if response['mismatched_parts'] else 'match'
            elif action == 'publish' and not response.get('deduplicated'):
                pub = publish_state(pub, entry['params']['candidate_id'],
                                    entry['params']['write_mode'], checked)
            elif action in ('stop', 'escalate'):
                ended = action
        return checked, cc_done, full, pub, 0 if ended else max(0, self.horizon - len(history)), ended

    def belief(self, history):
        """The prior restricted to alive(h) and renormalized; nothing coarser defines a belief."""
        alive = self.alive_from_history(history)
        if not alive:
            return {}
        total = self.mass(alive)
        return {self.latents[index]: self.weights[index] / total for index in alive}

    def value_from_history(self, history):
        alive = self.alive_from_history(history)
        checked, cc_done, full, pub, rem, ended = self.state_from_history(history)
        if not alive:
            return 0.0
        if ended:
            return self._end(alive, pub, ended == 'stop')
        return self.general(alive, checked, cc_done, full, pub, rem)

    def policy(self, history):
        alive = self.alive_from_history(history)
        checked, cc_done, full, pub, rem, ended = self.state_from_history(history)
        if ended or not alive or rem < 1:
            raise ValueError('no decision remains')
        return argmax_first(self.general_items(alive, checked, cc_done, full, pub, rem))


def oracle(profile, counts, regime_id, model='rev1', horizon=HORIZON):
    return Oracle(profile, counts, regime_id, model, horizon)


def solve(profile, regime_id, counts, model='rev1', horizon=HORIZON):
    """The general solver's root value: the INV-DP definition of E[U*]."""
    return Oracle(profile, counts, regime_id, model, horizon).general_root()


def compact_value(profile, regime_id, counts, model='rev1', horizon=HORIZON):
    return Oracle(profile, counts, regime_id, model, horizon).compact_root()


def belief(profile, regime_id, counts, history, model='rev1'):
    return Oracle(profile, counts, regime_id, model).belief(history)


def value_from_history(profile, regime_id, counts, history, model='rev1'):
    return Oracle(profile, counts, regime_id, model).value_from_history(history)


def policy(profile, regime_id, counts, history, model='rev1'):
    return Oracle(profile, counts, regime_id, model).policy(history)
