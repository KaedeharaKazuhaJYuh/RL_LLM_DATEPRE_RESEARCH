def _close(a, b, tol=1e-6):
    try: return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError): return a == b

def _same(actual, expected, tol=1e-6):
    if isinstance(expected, dict): return isinstance(actual, dict) and all(k in actual and _same(actual[k], v, tol) for k,v in expected.items())
    if isinstance(expected, list): return isinstance(actual, list) and len(actual)==len(expected) and all(_same(a,e,tol) for a,e in zip(actual,expected))
    return _close(actual, expected, tol)

def verify(result, gold, trace, constraints):
    required = all(k in result for k in ("answer", "evidence"))
    expected = gold.get("answer"); actual = result.get("answer")
    numeric = _close(actual, expected, gold.get("tolerance", 1e-6)) if expected is not None else required
    contract = constraints.get("validation", {})
    analysis = result.get("analysis", {})
    contract_ok = all(k in analysis for k in contract.get("required_analysis", []))
    if contract.get("operation") is not None: contract_ok = contract_ok and analysis.get("operation") == contract["operation"]
    reference = constraints.get("reference", {})
    reference_ok = _same(analysis, reference, gold.get("tolerance", 1e-6)) if reference else True
    allowed = set(constraints.get("allowed_tools", []))
    legal = all(step.get("tool") in allowed for step in trace)
    within_budget = len(trace) <= constraints.get("max_tool_calls", 10)
    cost = max(0.0, 1.0 - len(trace) / max(constraints.get("max_tool_calls", 10), 1))
    correctness = float(required and numeric and contract_ok and reference_ok)
    score = 0.6 * correctness + 0.2 * float(bool(result.get("evidence"))) + 0.2 * cost
    return {"passed": required and numeric and legal and within_budget and contract_ok and reference_ok, "score": score,
            "checks": {"structure": required, "answer": numeric, "contract": contract_ok, "reference": reference_ok, "legal": legal, "budget": within_budget}}

