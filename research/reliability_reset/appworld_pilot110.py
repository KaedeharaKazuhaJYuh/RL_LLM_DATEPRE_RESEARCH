"""Template-aware parsing of local continuations; raw output is never repaired."""

from .appworld_pilot195 import parse_proposal


def parse_local_continuation(content: str, *, prompt_opens_think: bool, finish_reason: str) -> dict:
    """Extract only text after the model closes a template-opened thinking segment."""
    if finish_reason != "stop":
        raise ValueError("unfinished_model_output")
    if prompt_opens_think:
        if "</think>" not in content:
            raise ValueError("unterminated_reasoning")
        content = content.split("</think>", 1)[1].strip()
    return parse_proposal(content)
