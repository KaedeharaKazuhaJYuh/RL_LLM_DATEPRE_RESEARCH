from dataclasses import dataclass
import numpy as np

@dataclass
class State:
    rows: int; cols: int; missing_rate: float; numeric_columns: int
    has_target: bool; needs_plot: bool; step: int = 0; verifier_score: float = 0.0

def rule_router(s: State) -> str:
    if s.missing_rate > .30: return "profile_missingness"
    if s.needs_plot: return "plot"
    if s.has_target: return "split_and_model"
    if s.numeric_columns >= 2: return "summarize_and_correlate"
    return "profile_schema"

class LinUCBBandit:
    def __init__(self, dim, actions, alpha=1.0):
        self.A = {a: np.eye(dim) for a in actions}; self.b = {a: np.zeros(dim) for a in actions}; self.alpha = alpha
    def select(self, x):
        return max(self.A, key=lambda a: self._ucb(a, x))
    def _ucb(self, a, x):
        inv = np.linalg.inv(self.A[a]); theta = inv @ self.b[a]
        return float(theta @ x + self.alpha * np.sqrt(x @ inv @ x))
    def update(self, a, x, reward):
        self.A[a] += np.outer(x, x); self.b[a] += reward * x

