"""
CFE Eval Engine — Dashboard
Run: streamlit run app/dashboard.py
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from library.scoring import load_taxonomy, get_factors_by_tier

st.set_page_config(
    page_title="CFE Eval Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

RUNS_DIR = Path(__file__).parent.parent / "data" / "runs"
SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


def load_runs(directory):
    runs = []
    if not directory.exists():
        return runs
    for f in sorted(directory.glob("*.json")):
        with open(f) as fh:
            runs.append(json.load(fh))
    return runs


def get_run_dir():
    if RUNS_DIR.exists() and list(RUNS_DIR.glob("*.json")):
        return RUNS_DIR
    return SAMPLES_DIR


# --- Sidebar ---

st.sidebar.title("CFE Eval Engine")
st.sidebar.markdown("Context First Evaluation")

page = st.sidebar.radio("Navigate", [
    "Corpus Overview",
    "Review Explorer",
    "Taxonomy Health",
    "Methodology"
])

run_dir = get_run_dir()
runs = load_runs(run_dir)
taxonomy = load_taxonomy(str(Path(__file__).parent.parent / "library" / "taxonomy.json"))
factors_by_tier = get_factors_by_tier(taxonomy)

st.sidebar.markdown("---")
st.sidebar.metric("Total Runs", len(runs))
st.sidebar.caption(f"Source: {run_dir}")


# ============================================================
# PAGE 1: Corpus Overview
# ============================================================

if page == "Corpus Overview":
    st.title("Corpus Overview")

    if not runs:
        st.warning("No runs found. Add JSON files to data/runs/ or data/samples/.")
        st.stop()

    # --- Top metrics ---
    col1, col2, col3, col4 = st.columns(4)

    verdicts = [r.get("verdict", {}).get("verdict", "?") if isinstance(r.get("verdict"), dict) else r.get("verdict", "?") for r in runs]
    verdict_counts = Counter(verdicts)

    accuracy_scores = []
    for r in runs:
        scores = r.get("scores", {})
        acc = scores.get("accuracy", {})
        if isinstance(acc, dict) and acc.get("applicable"):
            correct = acc.get("correct", 0)
            applicable = acc.get("applicable", 1)
            accuracy_scores.append(correct / applicable * 100)

    total_gaps = sum(r.get("scores", {}).get("coverage", {}).get("total_gaps", 0) for r in runs)
    total_exposures = sum(r.get("scores", {}).get("readiness", {}).get("total_exposures", 0) for r in runs)

    col1.metric("Reviews", len(runs))
    col2.metric("Avg Accuracy", f"{sum(accuracy_scores)/len(accuracy_scores):.0f}%" if accuracy_scores else "N/A")
    col3.metric("Coverage Gaps", total_gaps)
    col4.metric("Readiness Exposures", total_exposures)

    # --- Verdict distribution ---
    st.subheader("Verdict Distribution")
    verdict_df_data = [{"Verdict": v, "Count": c, "Percent": f"{c/len(runs)*100:.0f}%"}
                       for v, c in verdict_counts.most_common()]
    st.table(verdict_df_data)

    # --- Accuracy distribution ---
    if accuracy_scores:
        st.subheader("Accuracy Scores")
        st.bar_chart({"Accuracy %": accuracy_scores})

    # --- Most common coverage gaps ---
    st.subheader("Most Common Coverage Gaps")
    gap_counter = Counter()
    for r in runs:
        gaps = r.get("scores", {}).get("coverage", {}).get("gaps", [])
        for g in gaps:
            gap_counter[g.get("id", "?")] += 1
    if gap_counter:
        gap_data = [{"Factor": f, "Reviews": c} for f, c in gap_counter.most_common(10)]
        st.table(gap_data)
    else:
        st.info("No coverage gaps found across runs.")

    # --- Youth population flag ---
    st.subheader("Youth Population Flag")
    youth_relevant = sum(1 for r in runs if r.get("population_flags", {}).get("youth_relevant"))
    youth_zero = sum(1 for r in runs
                     if r.get("population_flags", {}).get("youth_relevant")
                     and r.get("population_flags", {}).get("youth_requirements_applied_by_system") == 0)
    ycol1, ycol2 = st.columns(2)
    ycol1.metric("Youth-relevant Reviews", youth_relevant)
    ycol2.metric("Zero Youth Reqs Applied", youth_zero)


# ============================================================
# PAGE 2: Review Explorer
# ============================================================

elif page == "Review Explorer":
    st.title("Review Explorer")

    if not runs:
        st.warning("No runs found.")
        st.stop()

    review_ids = [r.get("review_id", f"Run {i}") for i, r in enumerate(runs)]
    selected = st.selectbox("Select a review", review_ids)
    run = next(r for r in runs if r.get("review_id") == selected)

    # --- Verdict + Scores ---
    st.subheader("Scores")

    verdict = run.get("verdict", {})
    if isinstance(verdict, dict):
        v = verdict.get("verdict", "?")
        confidence = verdict.get("confidence", "?")
    else:
        v = str(verdict)
        confidence = "?"

    scores = run.get("scores", {})
    acc = scores.get("accuracy", {})
    cov = scores.get("coverage", {})
    rdy = scores.get("readiness", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Verdict", v)
    col2.metric("Accuracy", acc.get("score", "N/A"))
    col3.metric("Coverage Gaps", cov.get("total_gaps", 0))
    col4.metric("Readiness Exposures", rdy.get("total_exposures", 0))

    if acc.get("missed_factors"):
        st.error(f"**Missed factors:** {', '.join(acc['missed_factors'])}")

    # --- Coverage gaps detail ---
    gaps = cov.get("gaps", [])
    if gaps:
        st.subheader("Coverage Gaps")
        for g in gaps:
            relevance = g.get("relevance", "?")
            color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(relevance, "⚪")
            st.markdown(f"{color} **{g.get('id', '?')}** ({relevance}) — {g.get('reasoning', '')[:200]}")

    # --- Readiness exposures detail ---
    exposures = rdy.get("exposures", [])
    if exposures:
        st.subheader("Readiness Exposures")
        for e in exposures:
            relevance = e.get("relevance", "?")
            color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(relevance, "⚪")
            st.markdown(f"{color} **{e.get('id', '?')}** ({relevance}) — {e.get('regulation', '')} — {e.get('reasoning', '')[:200]}")

    # --- Factor evaluations ---
    st.subheader("Factor Evaluations")

    risk_factors = run.get("risk_factors", [])
    for tier_name, tier_label in [("established_risk", "Established"), ("emergent_risk", "Emergent"), ("projected_risk", "Projected")]:
        tier_factors = [rf for rf in risk_factors if rf.get("tier") == tier_name]
        if not tier_factors:
            continue
        st.markdown(f"**{tier_label}**")
        factor_table = []
        for rf in tier_factors:
            cfe = rf.get("cfe_says", "?")
            sys = rf.get("system_says", "?")
            agree = rf.get("agreement", "?")
            icon = {"IN_SCOPE": "🟢", "OUT_OF_SCOPE": "⚪", "INSUFFICIENT_EVIDENCE": "🟡"}.get(cfe, "❓")
            factor_table.append({
                "": icon,
                "Factor": rf.get("id", "?"),
                "CFE Says": cfe,
                "System Says": sys,
                "Agreement": agree,
                "Confidence": rf.get("confidence", "?")
            })
        st.table(factor_table)

        # Expandable detail for each factor with provenance + reasoning context
        for rf in tier_factors:
            provenance = rf.get("provenance", {})
            reasoning_ctx = rf.get("reasoning_context", {})
            if provenance or reasoning_ctx:
                with st.expander(f"Details: {rf.get('id', '?')}"):
                    if rf.get("evidence"):
                        st.markdown(f"**Evidence:** {rf['evidence']}")
                    if isinstance(provenance, dict) and provenance.get("source"):
                        st.markdown(f"**Provenance:** `{provenance.get('source', '')}` → `{provenance.get('extraction', '')}` → {provenance.get('path', '')}")
                    if isinstance(reasoning_ctx, dict):
                        if reasoning_ctx.get("considered"):
                            st.markdown(f"**Considered:** {', '.join(reasoning_ctx['considered'])}")
                        if reasoning_ctx.get("decided"):
                            st.markdown(f"**Decided:** {reasoning_ctx['decided']}")
                        if reasoning_ctx.get("uncertainty"):
                            st.markdown(f"**Uncertainty:** {reasoning_ctx['uncertainty']}")
                        if reasoning_ctx.get("what_would_change_my_mind"):
                            st.markdown(f"**What would change the call:** {reasoning_ctx['what_would_change_my_mind']}")

    # --- Grounding check ---
    grounding = run.get("grounding_check", {})
    if grounding:
        st.subheader("Evidence Grounding")
        gcol1, gcol2, gcol3 = st.columns(3)
        gcol1.metric("Grounded", f"{grounding.get('grounded', 0)}/{grounding.get('total_checked', 0)}")
        gcol2.metric("Ungrounded", grounding.get("ungrounded", 0))
        gcol3.metric("Provenance Verified", grounding.get("provenance_verified", 0))
        if grounding.get("ungrounded_factors"):
            for ug in grounding["ungrounded_factors"]:
                st.warning(f"**{ug.get('factor', '?')}** — match_ratio={ug.get('match_ratio', '?')} ({ug.get('method', 'fuzzy')}) — {ug.get('flag', '')}")

    # --- Youth flag ---
    pf = run.get("population_flags", {})
    if pf:
        st.subheader("Youth Population Flag")
        pcol1, pcol2, pcol3 = st.columns(3)
        pcol1.metric("Youth Relevant", "Yes" if pf.get("youth_relevant") else "No")
        pcol2.metric("Youth Reqs In Scope", pf.get("youth_requirements_in_scope", "?"))
        pcol3.metric("Youth Reqs Applied", pf.get("youth_requirements_applied_by_system", "?"))
        if pf.get("flag"):
            st.info(pf["flag"])

    # --- Entity map ---
    entity_map = run.get("entity_map", {})
    if entity_map:
        st.subheader("Entity Map")
        for key in ["users", "data", "models", "surfaces", "features", "data_flows"]:
            items = entity_map.get(key, [])
            if items:
                st.markdown(f"**{key.title()}:** {', '.join(items) if isinstance(items, list) else items}")

    # --- Evidence trail ---
    evidence = run.get("evidence_trail", [])
    if evidence:
        st.subheader("Evidence Trail")
        for step in evidence:
            if isinstance(step, dict):
                st.markdown(f"**Step {step.get('step', '?')}:** {step.get('action', '')} → {step.get('found', '')}")

    # --- Observed signals ---
    signals = run.get("observed_signals", [])
    if signals:
        st.subheader("Observed Signals")
        for s in signals:
            if isinstance(s, dict):
                status = s.get("graduation_status", "observed")
                st.markdown(f"**{s.get('signal', '?')}** — status: {status}, confidence: {s.get('confidence', '?')}")


# ============================================================
# PAGE 3: Taxonomy Health
# ============================================================

elif page == "Taxonomy Health":
    st.title("Taxonomy Health")

    if not runs:
        st.warning("No runs found.")
        st.stop()

    # --- Factor frequency ---
    st.subheader("Factor Application Rate")
    factor_in_scope = Counter()
    factor_total = Counter()

    for r in runs:
        for rf in r.get("risk_factors", []):
            fid = rf.get("id", "?")
            factor_total[fid] += 1
            if rf.get("cfe_says") == "IN_SCOPE":
                factor_in_scope[fid] += 1

    factor_rates = []
    for f in taxonomy["factors"]:
        fid = f["id"]
        total = factor_total.get(fid, 0)
        in_scope = factor_in_scope.get(fid, 0)
        rate = f"{in_scope/total*100:.0f}%" if total > 0 else "N/A"
        factor_rates.append({
            "Factor": fid,
            "Tier": f["tier"].replace("_risk", ""),
            "In Scope": in_scope,
            "Total": total,
            "Rate": rate,
            "Stage": f.get("stage", "established" if f["tier"] == "established_risk" else "emerging")
        })

    factor_rates.sort(key=lambda x: x["In Scope"], reverse=True)
    st.table(factor_rates)

    # --- Graduation pipeline ---
    st.subheader("Graduation Pipeline")
    all_signals = []
    for r in runs:
        for s in r.get("observed_signals", []):
            if isinstance(s, dict):
                all_signals.append(s.get("signal", "?"))

    signal_counts = Counter(all_signals)
    if signal_counts:
        pipeline_data = []
        for signal, count in signal_counts.most_common(20):
            stage = "observed"
            if count >= 25:
                stage = "recommended"
            elif count >= 5:
                stage = "emerging"
            pipeline_data.append({"Signal": signal, "Appearances": count, "Stage": stage})
        st.table(pipeline_data)
    else:
        st.info("No observed signals across runs yet.")

    # --- Under-scoping by factor ---
    st.subheader("Under-scoping Rate (Established Factors)")
    under_data = []
    for r in runs:
        acc = r.get("scores", {}).get("accuracy", {})
        for fid in acc.get("missed_factors", []):
            under_data.append(fid)

    if under_data:
        under_counts = Counter(under_data)
        under_table = [{"Factor": f, "Times Missed": c} for f, c in under_counts.most_common()]
        st.table(under_table)
    else:
        st.info("No under-scoping detected in current runs.")


# ============================================================
# PAGE 4: Methodology
# ============================================================

elif page == "Methodology":
    st.title("Methodology")

    st.header("Context First Evaluation")
    st.markdown("""
    CFE measures how well a privacy review system catches risk. Each run evaluates a single review
    across 29 risk factors organized into three tiers.
    """)

    st.subheader("Three Tiers, Three Questions")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Accuracy")
        st.markdown("**Established Risk** (14 factors)")
        st.markdown("_Did the system catch what it's supposed to catch?_")
        st.markdown("Performance metric — ratio of correct decisions to applicable factors.")
        st.markdown("Audience: **Auditors**")

    with col2:
        st.markdown("### Coverage")
        st.markdown("**Emergent Risk** (10 factors)")
        st.markdown("_Is the system looking for it?_")
        st.markdown("Discovery output — prioritized list of gaps the system doesn't track yet.")
        st.markdown("Audience: **System Owners**")

    with col3:
        st.markdown("### Readiness")
        st.markdown("**Projected Risk** (5 factors)")
        st.markdown("_Is the system prepared for what's coming?_")
        st.markdown("Discovery output — regulatory exposures not yet in the system.")
        st.markdown("Audience: **Policy & Legal**")

    st.subheader("Key Design Decisions")
    st.markdown("""
    1. **Taxonomy derived bottom-up** from 1,401 system requirements, corpus-mined LLM signals, and regulatory frameworks
    2. **Information separation** — the evaluator never sees the system's answer before making independent calls
    3. **Structural validation is insufficient** — enum compliance doesn't guarantee reasoning quality
    4. **Three output shapes** — Accuracy is a ratio, Coverage and Readiness are prioritized lists
    5. **Factor lifecycle** — observed → emerging → recommended → established
    """)

    st.subheader("Factor Lifecycle")
    st.markdown("""
    | Stage | Criteria | Meaning |
    |---|---|---|
    | **Observed** | Appears in evaluation | Signal detected |
    | **Emerging** | 5+ reviews | Pattern is real |
    | **Recommended** | 25+ reviews + evidence package | Ready for system adoption |
    | **Established** | System builds requirements | Scored in Accuracy |
    """)

    st.subheader("Bias Testing")
    st.markdown("""
    10 simple reviews tested as negative controls. 80 emergent factor evaluations.
    **0 false positives.** The emergent factors discriminate based on review content,
    not reflexively.
    """)

    st.subheader("Evolution")
    st.markdown("""
    - **v1**: No schema, no constraints. LLM freestyled everything.
    - **v2**: Schema enforcement, requirement text validation, 20 factors.
    - **v3**: Input data preservation, vocabulary constraints, 29 factors.
    - **v3.1**: Three-tier scoring, population flags, evidence packages, information separation.

    Each version was informed by what broke in the previous one.
    """)

    st.subheader("Population Flags")
    st.markdown("""
    Youth is the only population flag. It exists because:
    - Bright legal line (under 13/16/18)
    - Dedicated Risk Area at Meta
    - 292 requirements scattered across every category

    The flag checks whether the system applied youth-related requirements,
    not which age band applies. Age-band filtering is the requirement layer's job.
    """)
