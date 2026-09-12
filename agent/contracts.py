"""Translate declarative task contracts into permitted agent actions."""

ACTION_TO_TOOL = {
    "profile_schema": "load_table",
    "profile_missingness": "profile_missingness",
    "count_categories": "count_categories",
    "deduplicate": "deduplicate",
    "describe_numeric": "describe_numeric",
    "normalize_dates": "normalize_dates",
    "clip_outliers": "clip_outliers",
    "fill_missing": "fill_missing",
    "normalize_categories": "normalize_categories",
    "aggregate": "aggregate",
    "task_analysis": "task_analysis",
}

CAPABILITY_ACTIONS = {
    "overview": (
        "profile_schema", "profile_missingness", "count_categories",
        "deduplicate", "describe_numeric",
    ),
    "cleaning": (
        "deduplicate", "normalize_dates", "clip_outliers",
        "fill_missing", "normalize_categories",
    ),
    "aggregation": ("aggregate", "task_analysis"),
    "schema_profile": ("profile_schema",),
    "missingness_profile": ("profile_missingness",),
    "category_count": ("count_categories",),
    "deduplication": ("deduplicate",),
    "numeric_summary": ("describe_numeric",),
    "date_cleaning": ("normalize_dates",),
    "outlier_cleaning": ("clip_outliers",),
    "missing_value_cleaning": ("fill_missing",),
    "category_normalization": ("normalize_categories",),
    "monthly_aggregation": ("aggregate",),
    "general_analysis": ("task_analysis",),
}


def actions_from_contract(task):
    """Return contract-compatible actions that are also permitted by the task."""
    capabilities = task.get("contract", {}).get("required_capabilities", [])
    allowed_tools = set(task.get("allowed_tools", []))
    actions = []
    for capability in capabilities:
        for action in CAPABILITY_ACTIONS.get(capability, ()):
            if ACTION_TO_TOOL[action] in allowed_tools and action not in actions:
                actions.append(action)
    return actions

