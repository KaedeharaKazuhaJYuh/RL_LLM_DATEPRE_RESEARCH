from dataclasses import dataclass, field

@dataclass
class RunState:
    task_id: str
    features: list[float]
    step: int = 0
    verifier_score: float = 0.0
    remaining_calls: int = 8
    history: list[dict] = field(default_factory=list)
    done: bool = False

    def observe(self, action, observation, reward=0.0):
        self.history.append({"step": self.step, "action": action, "observation": observation, "reward": reward})
        self.step += 1; self.remaining_calls -= 1

