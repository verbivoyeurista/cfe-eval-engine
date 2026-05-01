"""Pipeline utilities: compare evaluated results and perform grounding checks."""
from pathlib import Path
from typing import Any, Dict, List

import json


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def grounding_check(item: Dict[str, Any], taxonomy: Dict[str, Any]) -> bool:
    """A simple grounding check: ensure category (if present) exists in taxonomy."""
    cat = item.get("category")
    if not cat:
        return False
    cats = {c["name"] for c in taxonomy.get("categories", [])}
    return cat in cats


def compare_evaluations(eval_a: List[Dict[str, Any]], eval_b: List[Dict[str, Any]], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two evaluation lists and return a summary including grounding results."""
    summary = {"total_a": len(eval_a), "total_b": len(eval_b), "grounding_failures": []}

    for item in eval_b:
        ok = grounding_check(item, taxonomy)
        if not ok:
            summary["grounding_failures"].append(item.get("id", item))

    return summary


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--b", type=Path, required=True)
    p.add_argument("--taxonomy", type=Path, required=True)
    args = p.parse_args()

    a = load_json(args.a)
    b = load_json(args.b)
    taxonomy = load_json(args.taxonomy)

    print(json.dumps(compare_evaluations(a, b, taxonomy), indent=2))
