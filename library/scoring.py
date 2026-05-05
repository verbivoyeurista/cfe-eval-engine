"""
CFE Scoring Logic

Three output shapes for three different questions:
- Accuracy: ratio (performance metric)
- Coverage: prioritized gap list (discovery)
- Readiness: prioritized exposure list (discovery)
"""

import json
from typing import List, Dict, Any

YOUTH_KEYWORDS = [
    'child', 'minor', 'youth', 'under 13', 'under 16', 'under 18',
    'u13', 'u16', 'u18', 'teen', 'tween', 'parental', 'age gate',
    'age-gate', 'young', 'age appropriate', 'age-appropriate'
]


def load_taxonomy(path: str = "library/taxonomy.json") -> Dict:
    with open(path) as f:
        return json.load(f)


def get_factors_by_tier(taxonomy: Dict) -> Dict[str, List[Dict]]:
    result = {"established_risk": [], "emergent_risk": [], "projected_risk": []}
    for factor in taxonomy["factors"]:
        result[factor["tier"]].append(factor)
    return result


def calculate_accuracy(risk_factors: List[Dict], raw_requirements: List[Dict], taxonomy: Dict) -> Dict:
    """
    Accuracy = correct / applicable

    Denominator (applicable): established_risk factors that have requirements
    present in raw_requirements, matched by system_category.

    Numerator (correct): factors where system and CFE agree —
    either both IN_SCOPE (caught) or both OUT_OF_SCOPE (correctly declined).

    Missed: CFE says IN_SCOPE but system says OUT_OF_SCOPE or NOT_EVALUATED.
    """
    established = [f for f in taxonomy["factors"] if f["tier"] == "established_risk"]

    req_categories = set()
    for req in raw_requirements:
        cat = req.get("category", "")
        if cat:
            req_categories.add(cat.upper().replace(" ", "_"))

    applicable_factors = []
    for factor in established:
        sys_cat = factor.get("system_category", "")
        if not sys_cat:
            continue
        sys_cat_normalized = sys_cat.upper().replace(" ", "_")
        if any(sys_cat_normalized in rc or rc in sys_cat_normalized for rc in req_categories):
            applicable_factors.append(factor["id"])

    caught = 0
    correctly_declined = 0
    missed_count = 0
    missed_factors = []

    for rf in risk_factors:
        if rf["id"] not in applicable_factors:
            continue
        if rf["tier"] != "established_risk":
            continue

        system = rf.get("system_says", "NOT_EVALUATED").upper()
        cfe = rf.get("cfe_says", "").upper()

        system_positive = system in ("IN_SCOPE", "ATTACHED", "FLAGGED")
        system_negative = system in ("OUT_OF_SCOPE", "NOT_EVALUATED", "NOT_ATTACHED")
        cfe_positive = cfe == "IN_SCOPE"
        cfe_negative = cfe == "OUT_OF_SCOPE"

        if system_positive and cfe_positive:
            caught += 1
        elif system_negative and cfe_negative:
            correctly_declined += 1
        elif cfe_positive and system_negative:
            missed_count += 1
            missed_factors.append(rf["id"])

    correct = caught + correctly_declined
    applicable = len(applicable_factors)

    return {
        "denominator_source": "requirement_categories",
        "applicable": applicable,
        "correct": correct,
        "missed": missed_count,
        "score": f"{correct}/{applicable}" if applicable > 0 else "N/A",
        "missed_factors": missed_factors
    }


def calculate_coverage(risk_factors: List[Dict]) -> Dict:
    """
    Coverage = prioritized list of emergent_risk factors where CFE says IN_SCOPE.
    Not a ratio — a discovery output.
    """
    gaps = []
    for rf in risk_factors:
        if rf["tier"] != "emergent_risk":
            continue
        if rf.get("cfe_says", "").upper() == "IN_SCOPE":
            gaps.append({
                "id": rf["id"],
                "relevance": rf.get("confidence", "medium"),
                "reasoning": rf.get("reasoning", "")
            })

    gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g["relevance"], 3))

    return {
        "gaps": gaps,
        "total_gaps": len(gaps)
    }


def calculate_readiness(risk_factors: List[Dict], taxonomy: Dict) -> Dict:
    """
    Readiness = prioritized list of projected_risk factors relevant to this review.
    Not a ratio — a discovery output.
    """
    projected = {f["id"]: f for f in taxonomy["factors"] if f["tier"] == "projected_risk"}
    exposures = []

    for rf in risk_factors:
        if rf["tier"] != "projected_risk":
            continue
        if rf.get("cfe_says", "").upper() == "IN_SCOPE":
            factor_def = projected.get(rf["id"], {})
            exposures.append({
                "id": rf["id"],
                "relevance": rf.get("confidence", "medium"),
                "regulation": factor_def.get("regulation", ""),
                "reasoning": rf.get("reasoning", "")
            })

    exposures.sort(key=lambda e: {"high": 0, "medium": 1, "low": 2}.get(e["relevance"], 3))

    return {
        "exposures": exposures,
        "total_exposures": len(exposures)
    }


def calculate_youth_flag(raw_requirements: List[Dict], project_context: Dict) -> Dict:
    """
    Youth population flag — checks whether the project impacts users under 18
    and whether the system applied youth-related requirements.
    """
    if not raw_requirements:
        return {
            "youth_relevant": None,
            "project_claims": None,
            "cfe_assessment": "Cannot assess — raw_requirements not populated",
            "confidence": None,
            "youth_requirements_in_scope": None,
            "youth_requirements_applied_by_system": None,
            "flag": "raw_requirements missing"
        }

    youth_reqs = []
    youth_applied = []

    for req in raw_requirements:
        text = (req.get("requirement_text") or "").lower()
        if any(kw in text for kw in YOUTH_KEYWORDS):
            youth_reqs.append(req)
            applicability = (req.get("applicability") or "").upper()
            if applicability not in ("OUT_OF_SCOPE_BY_DTS", "OUT_OF_SCOPE"):
                youth_applied.append(req)

    return {
        "youth_relevant": len(youth_reqs) > 0,
        "project_claims": project_context.get("age_range", "not stated"),
        "cfe_assessment": "",
        "confidence": "medium",
        "youth_requirements_in_scope": len(youth_reqs),
        "youth_requirements_applied_by_system": len(youth_applied),
        "flag": f"System applied {len(youth_applied)}/{len(youth_reqs)} youth-related requirements" if youth_reqs else ""
    }


def calculate_all_scores(risk_factors: List[Dict], raw_requirements: List[Dict],
                          taxonomy: Dict, project_context: Dict = None) -> Dict:
    """Calculate all three scores + population flags for a review."""
    return {
        "accuracy": calculate_accuracy(risk_factors, raw_requirements, taxonomy),
        "coverage": calculate_coverage(risk_factors),
        "readiness": calculate_readiness(risk_factors, taxonomy),
        "population_flags": calculate_youth_flag(raw_requirements, project_context or {})
    }
