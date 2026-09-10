import numpy as np

class LinUCBBandit:
    """Contextual bandit for high-level data-analysis actions."""
    def __init__(self, dim: int, actions: list[str], alpha: float = 1.0, rng=None):
        self.actions = actions; self.alpha = alpha; self.rng = rng
        self.A = {a: np.eye(dim) for a in actions}
        self.b = {a: np.zeros(dim) for a in actions}

    def select(self, x: np.ndarray) -> str:
        def ucb(a):
            inv = np.linalg.inv(self.A[a]); theta = inv @ self.b[a]
            return float(theta @ x + self.alpha * np.sqrt(x @ inv @ x))
        scores=np.asarray([ucb(a) for a in self.actions], dtype=float)
        best=np.flatnonzero(scores == scores.max())
        if self.rng is not None: return self.actions[int(self.rng.choice(best))]
        return self.actions[int(best[0])]

    def update(self, action: str, x: np.ndarray, reward: float) -> None:
        self.A[action] += np.outer(x, x); self.b[action] += reward * x

