from typing import Dict, Any


def score_item(item: Dict[str, Any], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    """Simple scoring example: produce a `score` and `confidence` for an item.

    This is a placeholder; replace with your domain logic.
    """
    # Example: if item has a numeric `value` use it as score
    value = item.get("value")
    if isinstance(value, (int, float)):
        score = float(value)
        confidence = 0.9
    else:
        score = 0.0
        confidence = 0.5

    return {"score": score, "confidence": confidence}


def apply_scoring(items, taxonomy):
    return [ {**item, **score_item(item, taxonomy)} for item in items ]
