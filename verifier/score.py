def _close(a, b, tol=1e-6):
    try: return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError): return a == b

def verify(result, gold, trace, constraints):
    required = all(k in result for k in ("answer", "evidence"))
    expected = gold.get("answer"); actual = result.get("answer")
    numeric = _close(actual, expected, gold.get("tolerance", 1e-6)) if expected is not None else required
    allowed = set(constraints.get("allowed_tools", []))
    legal = all(step.get("tool") in allowed for step in trace)
    within_budget = len(trace) <= constraints.get("max_tool_calls", 10)
    cost = max(0.0, 1.0 - len(trace) / max(constraints.get("max_tool_calls", 10), 1))
    score = 0.6 * float(required and numeric) + 0.2 * float(bool(result.get("evidence"))) + 0.2 * cost
    return {"passed": required and numeric and legal and within_budget, "score": score,
            "checks": {"structure": required, "answer": numeric, "legal": legal, "budget": within_budget}}

