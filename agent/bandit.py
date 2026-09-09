import numpy as np

class LinUCBBandit:
    """Contextual bandit for high-level data-analysis actions."""
    def __init__(self, dim: int, actions: list[str], alpha: float = 1.0):
        self.actions = actions; self.alpha = alpha
        self.A = {a: np.eye(dim) for a in actions}
        self.b = {a: np.zeros(dim) for a in actions}

    def select(self, x: np.ndarray) -> str:
        def ucb(a):
            inv = np.linalg.inv(self.A[a]); theta = inv @ self.b[a]
            return float(theta @ x + self.alpha * np.sqrt(x @ inv @ x))
        return max(self.actions, key=ucb)

    def update(self, action: str, x: np.ndarray, reward: float) -> None:
        self.A[action] += np.outer(x, x); self.b[action] += reward * x

