"""
CFE Compare Step

Step 3 of the pipeline. Merges:
- Gathered data (from gatherer agent)
- Evaluation (from evaluator agent)
- System answers (from gathered data's system_risk_factors)

Produces the final scored run with Accuracy, Coverage, Readiness, and population flags.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library.scoring import load_taxonomy, calculate_all_scores


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def derive_system_says(factor_id: str, factor_def: dict, raw_requirements: list) -> str:
    """
    Determine what the system said about a factor by checking
    whether requirements in the matching category were applied.
    """
    sys_cat = factor_def.get("system_category", "")
    if not sys_cat:
        return "NOT_EVALUATED"

    matching_reqs = [r for r in raw_requirements
                     if sys_cat in (r.get("category") or "")]

    if not matching_reqs:
        return "NOT_EVALUATED"

    applied = [r for r in matching_reqs
               if (r.get("applicability") or "").upper() not in
               ("OUT_OF_SCOPE_BY_DTS", "OUT_OF_SCOPE")]

    if applied:
        return "IN_SCOPE"
    else:
        return "OUT_OF_SCOPE"


def determine_agreement(cfe_says: str, system_says: str) -> str:
    if system_says == "NOT_EVALUATED":
        return "UNDETERMINED"
    cfe_upper = cfe_says.upper()
    sys_upper = system_says.upper()
    if cfe_upper == "INSUFFICIENT_EVIDENCE":
        return "UNDETERMINED"
    if (cfe_upper == "IN_SCOPE" and sys_upper == "IN_SCOPE") or \
       (cfe_upper == "OUT_OF_SCOPE" and sys_upper == "OUT_OF_SCOPE"):
        return "AGREE"
    return "DISAGREE"


def determine_verdict(accuracy: dict, coverage: dict) -> dict:
    """
    Verdict is driven by Accuracy and Coverage.
    Readiness is informational only.
    """
    missed = accuracy.get("missed", 0)
    missed_factors = accuracy.get("missed_factors", [])
    gaps = coverage.get("total_gaps", 0)
    applicable = accuracy.get("applicable", 0)

    if applicable == 0:
        return {
            "verdict": "NEEDS_MORE_INFO",
            "mechanism": "No applicable established factors found",
            "confidence": "low",
            "reasoning_summary": "Cannot assess — no requirement categories matched."
        }

    if missed == 0 and gaps == 0:
        return {
            "verdict": "NO_ESCALATION",
            "mechanism": "System performed correctly on all applicable factors with no emergent gaps",
            "confidence": "high",
            "reasoning_summary": f"Accuracy {accuracy['score']}. No coverage gaps."
        }

    if missed == 0 and gaps > 0:
        return {
            "verdict": "NO_ESCALATION",
            "mechanism": "System performed correctly on established factors. Emergent gaps are informational.",
            "confidence": "high",
            "reasoning_summary": f"Accuracy {accuracy['score']}. {gaps} coverage gaps identified for system expansion."
        }

    if missed > 0:
        return {
            "verdict": "UNDER_SCOPED",
            "mechanism": f"System missed {missed} established factor(s): {', '.join(missed_factors)}",
            "confidence": "high",
            "reasoning_summary": f"Accuracy {accuracy['score']}. Missed: {', '.join(missed_factors)}. {gaps} additional coverage gaps."
        }

    return {
        "verdict": "NEEDS_MORE_INFO",
        "mechanism": "Could not determine verdict",
        "confidence": "low",
        "reasoning_summary": "Unexpected state in verdict logic."
    }


def resolve_provenance_path(input_data: dict, source_path: str) -> str:
    """
    Follow a provenance source path like 'input_data.intake.description'
    and return the text at that location. Returns empty string if path doesn't resolve.
    """
    if not source_path:
        return ""

    parts = source_path.replace("input_data.", "").split(".")
    current = input_data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, "")
        elif isinstance(current, list):
            try:
                idx = int(part.replace("[", "").replace("]", ""))
                current = current[idx] if idx < len(current) else ""
            except (ValueError, IndexError):
                return ""
        else:
            return ""

    if isinstance(current, str):
        return current.lower()
    elif isinstance(current, list):
        return " ".join(str(v).lower() for v in current)
    elif isinstance(current, dict):
        return " ".join(str(v).lower() for v in current.values() if isinstance(v, str))
    return str(current).lower()


def ground_check(evaluated_factors: list, input_data: dict) -> dict:
    """
    Evidence grounding check — verify that evidence strings in factor evaluations
    can be traced back to the gathered input data. Catches fabrication and confabulation.

    Uses provenance pointers when available (direct path verification).
    Falls back to fuzzy word matching when provenance is absent.

    Returns a grounding report with flagged factors.
    """
    intake = input_data.get("intake", {})
    raw_reqs = input_data.get("raw_requirements", [])
    entity_map = input_data.get("entity_map", {})

    searchable_text = ""

    if isinstance(intake, dict):
        for key, val in intake.items():
            if isinstance(val, str):
                searchable_text += " " + val.lower()
            elif isinstance(val, list):
                searchable_text += " " + " ".join(str(v).lower() for v in val)

    for req in raw_reqs:
        if isinstance(req, dict):
            text = req.get("requirement_text", "")
            if text:
                searchable_text += " " + text.lower()

    if isinstance(entity_map, dict):
        for key, vals in entity_map.items():
            if isinstance(vals, list):
                searchable_text += " " + " ".join(str(v).lower() for v in vals)
            elif isinstance(vals, str):
                searchable_text += " " + vals.lower()

    grounded = []
    ungrounded = []
    skipped = []
    provenance_verified = 0

    for rf in evaluated_factors:
        evidence = rf.get("evidence", "")
        if not evidence or len(evidence) < 10:
            skipped.append(rf.get("id", "?"))
            continue

        provenance = rf.get("provenance", {})
        source_path = provenance.get("source", "") if isinstance(provenance, dict) else ""

        if source_path:
            source_text = resolve_provenance_path(input_data, source_path)
            if source_text:
                evidence_words = [w for w in evidence.lower().split() if len(w) > 3]
                if evidence_words:
                    matches = sum(1 for w in evidence_words if w in source_text)
                    match_ratio = matches / len(evidence_words)
                    if match_ratio >= 0.25:
                        grounded.append(rf.get("id", "?"))
                        provenance_verified += 1
                        continue
                    else:
                        ungrounded.append({
                            "factor": rf.get("id", "?"),
                            "evidence": evidence[:200],
                            "match_ratio": round(match_ratio, 2),
                            "method": "provenance",
                            "source_path": source_path,
                            "flag": "Evidence does not match provenance source path"
                        })
                        continue

        evidence_words = [w for w in evidence.lower().split() if len(w) > 3]
        if not evidence_words:
            skipped.append(rf.get("id", "?"))
            continue

        matches = sum(1 for w in evidence_words if w in searchable_text)
        match_ratio = matches / len(evidence_words)

        if match_ratio >= 0.3:
            grounded.append(rf.get("id", "?"))
        else:
            ungrounded.append({
                "factor": rf.get("id", "?"),
                "evidence": evidence[:200],
                "match_ratio": round(match_ratio, 2),
                "method": "fuzzy",
                "flag": "Evidence may be fabricated — low overlap with gathered input data"
            })

    return {
        "grounded": len(grounded),
        "ungrounded": len(ungrounded),
        "skipped": len(skipped),
        "provenance_verified": provenance_verified,
        "ungrounded_factors": ungrounded,
        "total_checked": len(grounded) + len(ungrounded)
    }


def compare_review(review_id: str, base_dir: str = ".") -> dict:
    """
    Merge gathered data + evaluation + system answers into a final scored run.
    """
    gathered = load_json(f"{base_dir}/data/gathered/{review_id}.json")
    evaluated = load_json(f"{base_dir}/data/evaluated/{review_id}.json")
    taxonomy = load_taxonomy(f"{base_dir}/library/taxonomy.json")

    factor_defs = {f["id"]: f for f in taxonomy["factors"]}
    input_data = gathered.get("input_data", {})
    raw_requirements = input_data.get("raw_requirements", gathered.get("raw_requirements", []))

    merged_factors = []
    for rf in evaluated["risk_factors"]:
        factor_def = factor_defs.get(rf["id"], {})

        system_says = derive_system_says(rf["id"], factor_def, raw_requirements)
        agreement = determine_agreement(rf.get("cfe_says", ""), system_says)

        merged_factors.append({
            **rf,
            "system_says": system_says,
            "agreement": agreement
        })

    scores = calculate_all_scores(
        merged_factors,
        raw_requirements,
        taxonomy,
        gathered.get("intake", {})
    )

    verdict = determine_verdict(scores["accuracy"], scores["coverage"])

    grounding = ground_check(evaluated["risk_factors"], input_data)

    final_run = {
        "schema_version": "3.1",
        "review_id": review_id,
        "review_name": gathered.get("review_summary", {}).get("display_name", ""),
        "run_date": datetime.utcnow().isoformat() + "Z",
        "input_data": gathered,
        "entity_map": gathered.get("entity_map", {}),
        "risk_factors": merged_factors,
        "observed_signals": evaluated.get("observed_signals", []),
        "scores": scores,
        "population_flags": scores.pop("population_flags", {}),
        "requirements": {
            "total": gathered.get("raw_requirements_count", len(raw_requirements)),
        },
        "evidence_trail": evaluated.get("evidence_trail", []),
        "cross_layer_contradictions": [],
        "key_findings": [],
        "verdict": verdict,
        "grounding_check": grounding,
        "validation": {
            "schema_version": "3.1",
            "factors_count": len(merged_factors),
            "all_canonical": all(rf["id"] in factor_defs for rf in merged_factors),
            "raw_requirements_populated": len(raw_requirements) > 0,
            "population_flags_present": True,
            "evidence_grounded": grounding["ungrounded"] == 0
        }
    }

    output_path = f"{base_dir}/data/runs/{review_id}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(final_run, f, indent=2)

    print(f"Saved: {output_path}")
    print(f"Accuracy: {scores['accuracy']['score']}")
    print(f"Coverage: {scores['coverage']['total_gaps']} gaps")
    print(f"Readiness: {scores['readiness']['total_exposures']} exposures")
    print(f"Verdict: {verdict['verdict']}")
    print(f"Grounding: {grounding['grounded']}/{grounding['total_checked']} evidence claims grounded")
    if grounding["ungrounded"] > 0:
        print(f"  WARNING: {grounding['ungrounded']} factors have ungrounded evidence (possible fabrication)")
        for ug in grounding["ungrounded_factors"]:
            print(f"    {ug['factor']}: match_ratio={ug['match_ratio']} — {ug['flag']}")

    return final_run


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare.py REVIEW_ID")
        sys.exit(1)
    compare_review(sys.argv[1])
