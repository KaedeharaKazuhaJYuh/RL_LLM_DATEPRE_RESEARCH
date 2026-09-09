from dataclasses import dataclass

@dataclass
class AgentState:
    missing_rate: float = 0.0
    numeric_columns: int = 0
    has_target: bool = False
    needs_plot: bool = False
    step: int = 0
    verifier_score: float = 0.0
    remaining_calls: int = 8
    last_error: str | None = None

def rule_router(s: AgentState) -> str:
    if s.remaining_calls <= 1: return "stop"
    if s.last_error: return "retry"
    if s.missing_rate > 0.30: return "profile_missingness"
    if s.needs_plot: return "visualize"
    if s.has_target: return "model"
    if s.numeric_columns >= 2: return "aggregate"
    return "profile_schema"

