"""
CFE Validate Step

Compares CFE's scored runs against external ground truth:
- Audit ground truth (PO-selected risk factors vs auditor-identified missed factors)
- Forest GT labels (SME attach/not-attach decisions per requirement)

Produces precision, recall, F1, per-factor breakdown, and confusion matrix.

Usage:
    python pipeline/validate.py --ground-truth audit_failed.csv
    python pipeline/validate.py --ground-truth forest_gt.csv --type forest
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mapping from audit risk factor names to CFE factor IDs.
# One audit factor may map to multiple CFE factors (OR relationship).
AUDIT_TO_CFE = {
    "consent_transparency_privacy_settings_flow": ["consent", "user_settings", "notice", "visibility"],
    "ads_personalization": ["profiling_inference"],
    "third_party_data_collection": ["external_sharing"],
    "third_party_data_sharing": ["external_sharing", "external_use"],
    "restricted_data": ["protected_characteristics"],
    "gen_ai": ["genai_safety"],
    "targeted_to_children_or_minors": ["children_by_design"],
    "cross_app_sharing": ["cross_border_transfer"],
    "consumer_messaging": ["notice"],
    "user_data": ["data_collection_minimization", "purpose_limitation"],
    "deletion_exemption": ["deletion"],
    "sharing_edited_video_or_audio_content": ["integrity_enforcement"],
    "cookies": ["notice", "consent"],
    "anti_scraping": ["external_use"],
}

# Reverse mapping: CFE factor ID -> set of audit names that map to it
CFE_TO_AUDIT = defaultdict(set)
for audit_name, cfe_ids in AUDIT_TO_CFE.items():
    for cfe_id in cfe_ids:
        CFE_TO_AUDIT[cfe_id].add(audit_name)


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def normalize_factor_name(name: str) -> str:
    """Normalize an audit factor name for matching."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def get_cfe_in_scope_factors(run: dict) -> Set[str]:
    """Extract set of factor IDs where CFE says IN_SCOPE."""
    factors = set()
    for rf in run.get("risk_factors", []):
        if rf.get("cfe_says", "").upper() == "IN_SCOPE":
            factors.add(rf["id"])
    return factors


def map_audit_factors_to_cfe(audit_factors: List[str]) -> Set[str]:
    """Map a list of audit factor names to the corresponding CFE factor IDs."""
    cfe_factors = set()
    for name in audit_factors:
        normalized = normalize_factor_name(name)
        if normalized in AUDIT_TO_CFE:
            cfe_factors.update(AUDIT_TO_CFE[normalized])
        else:
            # Try partial match
            for key, vals in AUDIT_TO_CFE.items():
                if normalized in key or key in normalized:
                    cfe_factors.update(vals)
                    break
    return cfe_factors


def parse_factor_list(raw: str) -> List[str]:
    """Parse a comma/semicolon-separated factor list from CSV cell."""
    if not raw or raw.strip() in ("", "N/A", "None", "-"):
        return []
    separators = [";", ",", "|"]
    items = [raw]
    for sep in separators:
        new_items = []
        for item in items:
            new_items.extend(item.split(sep))
        items = new_items
    return [s.strip() for s in items if s.strip()]


def validate_audit(ground_truth_path: str, runs_dir: str) -> dict:
    """
    Validate CFE runs against audit ground truth.

    CSV columns expected: Review ID, PO Selected RFs, Auditor Missed RFs, Auditor Rationale
    """
    gt_rows = load_csv(ground_truth_path)
    results = []
    all_cfe_positives = 0
    all_true_positives = 0
    all_gt_positives = 0
    per_factor_tp = defaultdict(int)
    per_factor_fp = defaultdict(int)
    per_factor_fn = defaultdict(int)
    confusion = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    skipped = []

    for row in gt_rows:
        review_id = row.get("Review ID", "").strip()
        if not review_id:
            continue

        run_path = os.path.join(runs_dir, f"{review_id}.json")
        if not os.path.exists(run_path):
            skipped.append({"review_id": review_id, "reason": "Run file not found"})
            continue

        run = load_json(run_path)
        cfe_flags = get_cfe_in_scope_factors(run)

        # Ground truth: auditor's missed RFs are factors the PO SHOULD have flagged
        # These represent the "correct" set of factors that should be IN_SCOPE
        po_selected = parse_factor_list(row.get("PO Selected RFs", ""))
        auditor_missed = parse_factor_list(row.get("Auditor Missed RFs", ""))

        # The full ground truth positive set = PO selected + auditor missed
        # (everything that should have been flagged)
        gt_audit_factors = po_selected + auditor_missed
        gt_cfe_factors = map_audit_factors_to_cfe(gt_audit_factors)

        # Also map just the PO-selected (system already caught these)
        po_cfe_factors = map_audit_factors_to_cfe(po_selected)

        # Compare
        tp = cfe_flags & gt_cfe_factors  # CFE flagged, GT agrees
        fp = cfe_flags - gt_cfe_factors  # CFE flagged, GT doesn't have it
        fn = gt_cfe_factors - cfe_flags  # GT says flag, CFE missed

        all_true_positives += len(tp)
        all_cfe_positives += len(cfe_flags)
        all_gt_positives += len(gt_cfe_factors)

        confusion["tp"] += len(tp)
        confusion["fp"] += len(fp)
        confusion["fn"] += len(fn)

        for f in tp:
            per_factor_tp[f] += 1
        for f in fp:
            per_factor_fp[f] += 1
        for f in fn:
            per_factor_fn[f] += 1

        results.append({
            "review_id": review_id,
            "cfe_flags": sorted(cfe_flags),
            "gt_factors": sorted(gt_cfe_factors),
            "agreement": sorted(tp),
            "cfe_only": sorted(fp),
            "gt_only": sorted(fn),
            "agreement_count": len(tp),
            "cfe_only_count": len(fp),
            "gt_only_count": len(fn),
            "auditor_rationale": row.get("Auditor Rationale", ""),
        })

    return _build_report(results, confusion, per_factor_tp, per_factor_fp,
                         per_factor_fn, skipped, "audit")


def validate_forest(ground_truth_path: str, runs_dir: str) -> dict:
    """
    Validate CFE runs against Forest GT labels.

    CSV columns expected: Review ID, Requirement ID, SME Label (Attach/Not Attach), SME Rationale
    """
    gt_rows = load_csv(ground_truth_path)

    # Group GT by review_id
    gt_by_review = defaultdict(list)
    for row in gt_rows:
        review_id = row.get("Review ID", "").strip()
        if review_id:
            gt_by_review[review_id].append(row)

    results = []
    all_cfe_positives = 0
    all_true_positives = 0
    all_gt_positives = 0
    per_factor_tp = defaultdict(int)
    per_factor_fp = defaultdict(int)
    per_factor_fn = defaultdict(int)
    confusion = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    skipped = []

    for review_id, gt_entries in gt_by_review.items():
        run_path = os.path.join(runs_dir, f"{review_id}.json")
        if not os.path.exists(run_path):
            skipped.append({"review_id": review_id, "reason": "Run file not found"})
            continue

        run = load_json(run_path)
        cfe_flags = get_cfe_in_scope_factors(run)

        # Build GT set from SME labels: "Attach" means factor should be IN_SCOPE
        gt_factors = set()
        for entry in gt_entries:
            label = entry.get("SME Label", "").strip().lower()
            req_id = entry.get("Requirement ID", "").strip()
            if label in ("attach", "in_scope", "yes", "true"):
                # Requirement ID may contain factor info — extract category
                # Match against run's raw_requirements to find the factor
                factor_id = _requirement_to_factor(req_id, run)
                if factor_id:
                    gt_factors.add(factor_id)

        tp = cfe_flags & gt_factors
        fp = cfe_flags - gt_factors
        fn = gt_factors - cfe_flags

        all_true_positives += len(tp)
        all_cfe_positives += len(cfe_flags)
        all_gt_positives += len(gt_factors)

        confusion["tp"] += len(tp)
        confusion["fp"] += len(fp)
        confusion["fn"] += len(fn)

        for f in tp:
            per_factor_tp[f] += 1
        for f in fp:
            per_factor_fp[f] += 1
        for f in fn:
            per_factor_fn[f] += 1

        results.append({
            "review_id": review_id,
            "cfe_flags": sorted(cfe_flags),
            "gt_factors": sorted(gt_factors),
            "agreement": sorted(tp),
            "cfe_only": sorted(fp),
            "gt_only": sorted(fn),
            "agreement_count": len(tp),
            "cfe_only_count": len(fp),
            "gt_only_count": len(fn),
        })

    return _build_report(results, confusion, per_factor_tp, per_factor_fp,
                         per_factor_fn, skipped, "forest")


def _requirement_to_factor(req_id: str, run: dict) -> str:
    """
    Map a requirement ID to a CFE factor ID by looking up the requirement's
    category in the run's raw_requirements and then mapping to factor taxonomy.
    """
    raw_reqs = (run.get("input_data", {}).get("input_data", {})
                .get("raw_requirements", []))
    if not raw_reqs:
        raw_reqs = run.get("input_data", {}).get("raw_requirements", [])

    for req in raw_reqs:
        if req.get("id", "") == req_id:
            category = req.get("category", "")
            return _category_to_factor(category)

    # Fallback: try matching by partial ID
    for req in raw_reqs:
        if req_id in req.get("id", ""):
            category = req.get("category", "")
            return _category_to_factor(category)

    return ""


def _category_to_factor(category: str) -> str:
    """Map a requirement category like SECURITY__EXTERNAL_USE to a CFE factor ID."""
    if not category:
        return ""
    cat_lower = category.lower().replace("__", "_")
    # Direct mappings from common category patterns
    category_factor_map = {
        "external_sharing": "external_sharing",
        "external_use": "external_use",
        "deletion": "deletion",
        "notice": "notice",
        "consent": "consent",
        "purpose_limitation": "purpose_limitation",
        "data_collection_minimization": "data_collection_minimization",
        "cross_border_transfer": "cross_border_transfer",
        "children_by_design": "children_by_design",
        "profiling_inference": "profiling_inference",
        "protected_characteristics": "protected_characteristics",
        "integrity_enforcement": "integrity_enforcement",
        "genai_safety": "genai_safety",
        "visibility": "visibility",
        "user_settings": "user_settings",
    }
    for pattern, factor_id in category_factor_map.items():
        if pattern in cat_lower:
            return factor_id
    # Last part of category often matches
    parts = cat_lower.split("_")
    if len(parts) >= 2:
        suffix = "_".join(parts[-2:])
        if suffix in category_factor_map:
            return category_factor_map[suffix]
    return ""


def _build_report(results: list, confusion: dict, per_factor_tp: dict,
                  per_factor_fp: dict, per_factor_fn: dict,
                  skipped: list, gt_type: str) -> dict:
    """Build the final validation report from computed metrics."""
    tp = confusion["tp"]
    fp = confusion["fp"]
    fn = confusion["fn"]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Per-factor breakdown
    all_factors = set(per_factor_tp.keys()) | set(per_factor_fp.keys()) | set(per_factor_fn.keys())
    per_factor = {}
    for f in sorted(all_factors):
        f_tp = per_factor_tp[f]
        f_fp = per_factor_fp[f]
        f_fn = per_factor_fn[f]
        f_precision = f_tp / (f_tp + f_fp) if (f_tp + f_fp) > 0 else 0.0
        f_recall = f_tp / (f_tp + f_fn) if (f_tp + f_fn) > 0 else 0.0
        f_f1 = (2 * f_precision * f_recall / (f_precision + f_recall)) if (f_precision + f_recall) > 0 else 0.0
        per_factor[f] = {
            "tp": f_tp,
            "fp": f_fp,
            "fn": f_fn,
            "precision": round(f_precision, 4),
            "recall": round(f_recall, 4),
            "f1": round(f_f1, 4),
        }

    # Categorize disagreements
    cfe_only_factors = defaultdict(int)
    gt_only_factors = defaultdict(int)
    for r in results:
        for f in r.get("cfe_only", []):
            cfe_only_factors[f] += 1
        for f in r.get("gt_only", []):
            gt_only_factors[f] += 1

    report = {
        "validation_type": gt_type,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "reviews_evaluated": len(results),
            "reviews_skipped": len(skipped),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "confusion_matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
        },
        "per_factor_breakdown": per_factor,
        "disagreement_analysis": {
            "cfe_only_frequency": dict(sorted(cfe_only_factors.items(), key=lambda x: -x[1])),
            "gt_only_frequency": dict(sorted(gt_only_factors.items(), key=lambda x: -x[1])),
        },
        "per_review_results": results,
        "skipped_reviews": skipped,
    }

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate CFE scored runs against ground truth"
    )
    parser.add_argument(
        "--ground-truth", required=True,
        help="Path to ground truth CSV (audit or forest format)"
    )
    parser.add_argument(
        "--type", choices=["audit", "forest"], default="audit",
        help="Ground truth type: 'audit' (default) or 'forest'"
    )
    parser.add_argument(
        "--runs-dir", default=None,
        help="Path to runs directory (default: data/runs/)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path for report (default: data/validation/validation_report.json)"
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runs_dir = args.runs_dir or os.path.join(base_dir, "data", "runs")
    output_path = args.output or os.path.join(base_dir, "data", "validation", "validation_report.json")

    if args.type == "forest":
        report = validate_forest(args.ground_truth, runs_dir)
    else:
        report = validate_audit(args.ground_truth, runs_dir)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    s = report["summary"]
    cm = report["confusion_matrix"]
    print(f"\n{'='*60}")
    print(f"  CFE Validation Report ({report['validation_type']} ground truth)")
    print(f"{'='*60}")
    print(f"  Reviews evaluated:  {s['reviews_evaluated']}")
    print(f"  Reviews skipped:    {s['reviews_skipped']}")
    print(f"{'─'*60}")
    print(f"  Precision:          {s['precision']:.1%}")
    print(f"  Recall:             {s['recall']:.1%}")
    print(f"  F1 Score:           {s['f1']:.1%}")
    print(f"{'─'*60}")
    print(f"  Confusion Matrix:")
    print(f"    True Positives:   {cm['true_positive']}")
    print(f"    False Positives:  {cm['false_positive']}")
    print(f"    False Negatives:  {cm['false_negative']}")
    print(f"{'─'*60}")

    # Per-factor table
    pf = report["per_factor_breakdown"]
    if pf:
        print(f"  Per-Factor Breakdown:")
        print(f"  {'Factor':<35} {'Prec':>6} {'Rec':>6} {'F1':>6} {'TP':>4} {'FP':>4} {'FN':>4}")
        print(f"  {'─'*35} {'─'*6} {'─'*6} {'─'*6} {'─'*4} {'─'*4} {'─'*4}")
        for factor, metrics in sorted(pf.items(), key=lambda x: -x[1]["f1"]):
            print(f"  {factor:<35} {metrics['precision']:>5.0%} {metrics['recall']:>5.0%} "
                  f"{metrics['f1']:>5.0%} {metrics['tp']:>4} {metrics['fp']:>4} {metrics['fn']:>4}")

    # Top disagreements
    da = report["disagreement_analysis"]
    if da["gt_only_frequency"]:
        print(f"{'─'*60}")
        print(f"  Top CFE Misses (GT says flag, CFE missed):")
        for factor, count in list(da["gt_only_frequency"].items())[:5]:
            print(f"    {factor}: {count} reviews")

    if da["cfe_only_frequency"]:
        print(f"  Top CFE Over-flags (CFE says flag, GT disagrees):")
        for factor, count in list(da["cfe_only_frequency"].items())[:5]:
            print(f"    {factor}: {count} reviews")

    print(f"{'='*60}")
    print(f"  Report saved: {output_path}")
    print()


if __name__ == "__main__":
    main()
