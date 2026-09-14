"""Tool availability only; no task-ID or answer-family masking."""
from agent.tools import ACTIONS
def actions_from_contract(task):return [a for a in ACTIONS if a in task.get('allowed_tools',ACTIONS)]
