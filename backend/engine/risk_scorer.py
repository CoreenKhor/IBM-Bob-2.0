"""
Step 5 — Risk Scorer

Applies the 4-factor blast radius risk matrix and returns a risk breakdown dict
with an overall CRITICAL / HIGH / MEDIUM / LOW rating.
"""


def score_risk(dependencies: list[dict], contracts: list[dict], tests: list[dict]) -> dict:
    """
    Evaluate the 4-factor risk matrix:
      1. api_boundary         — based on contract hazards found
      2. data_persistence     — based on db_schema hazards found
      3. dependency_centrality — based on number of callers found
      4. test_coverage        — based on test files found vs callers

    Returns:
      {
        api_boundary, data_persistence, dependency_centrality, test_coverage,
        overall
      }
    """
    # Factor 1 — API boundary
    api_hazards = [c for c in contracts if c.get("type") == "api_contract"]
    if len(api_hazards) >= 2:
        api_score = 3  # critical
    elif len(api_hazards) == 1:
        api_score = 2  # high
    else:
        api_score = 1  # low

    # Factor 2 — Data persistence
    db_hazards = [c for c in contracts if c.get("type") == "db_schema"]
    if len(db_hazards) >= 2:
        db_score = 3
    elif len(db_hazards) == 1:
        db_score = 2
    else:
        db_score = 1

    # Factor 3 — Dependency centrality
    direct_count = sum(1 for d in dependencies if d.get("depth") == 1)
    if direct_count >= 4:
        dep_score = 3
    elif direct_count >= 2:
        dep_score = 2
    else:
        dep_score = 1

    # Factor 4 — Test coverage (inverse: fewer tests = higher risk)
    test_count = len(tests)
    if test_count == 0:
        test_score = 3
    elif test_count == 1:
        test_score = 2
    else:
        test_score = 1

    overall_score = max(api_score, db_score, dep_score, test_score)

    label_map = {1: "low", 2: "medium", 3: "high"}

    return {
        "api_boundary": label_map[api_score],
        "data_persistence": label_map[db_score],
        "dependency_centrality": label_map[dep_score],
        "test_coverage": label_map[test_score],
        "overall": _overall_label(overall_score, direct_count),
    }


def _overall_label(score: int, direct_count: int) -> str:
    if score == 3 or direct_count >= 4:
        return "CRITICAL"
    if score == 2 or direct_count >= 2:
        return "HIGH"
    if direct_count == 1:
        return "MEDIUM"
    return "LOW"
