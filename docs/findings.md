# CFE Findings

Research findings from ~3 months of evaluation work (Feb-May 2026). All numbers from production privacy reviews at a large tech company.

---

## Corpus Scale

- **494 CFE run JSONs** (all v2+ schema, normalized April 2026)
- **280+ gathered reviews** in this repo (raw data)
- **150+ scored runs** (full pipeline output with verdicts)
- **33,000+ requirements** across the corpus (100% text coverage in v2+)
- **152 blind-validated runs** against expert ground truth
- **812 audit failures** analyzed for root cause

---

## The Core Finding: 99.56% Routing Gap

Under-scoping -- the system missing risk factors that should apply -- is almost entirely a routing problem.

**99.56% of misses are routing gaps.** The system never asked the right question. The decision tree didn't have a path to the correct answer. This is NOT assessor error (the human answering the DT questions). It's a system design flaw.

The remaining 0.44% are actual assessor errors (wrong answer to a correctly-asked question).

---

## Validation Against Ground Truth

### Review-Level Recall: 89-92%

152 runs evaluated blind and scored against expert ground truth (SME labels). Three-way comparison: CFE vs Forest (production deterministic system) vs SME.

- Kit (Claude Code): 11/12 matched reviews correct
- MM (MetaMate): 8/9 matched reviews correct
- One miss: L1418370PRV2 -- methodology disagreement ("always attach" rule vs CFE's context evaluation)
- Cross-checked independently by both agents

### Factor-Level Precision: Artificially Low

Factor-level precision appears low (3.7-3.9%) because the ground truth only covers Restricted Data requirements. CFE evaluates all 29 factors, so "false positives" are just factors the GT doesn't cover.

### Comparison to Production ML (GRIN)

GRIN (production LLM-based recommendations): 64.9% recall, 48.2% precision.
CFE: 89-92% recall at review level. Competitive with production ML using structured evaluation instead of black-box models.

---

## Under-Scoping: 71% Across Both Systems

323 comparable reviews analyzed (179 Forest, 144 DT). Both systems show the same ~71% under-scoping rate:
- Forest: 71.5%
- Decision Trees: 70.1%

This means the problem is **upstream of the scoping tool**. Replacing DTs with Forest didn't fix it because both inherit the same factor-attachment gaps.

---

## Specific Gap Rates

| Factor | Gap Rate | Notes |
|--------|----------|-------|
| Data Retention | 100% | 0-for-39. Wrong on every single decision. |
| Fairness/Bias | 100% | Doesn't exist as a risk factor in the framework. |
| Protected Characteristics | 0% recall in validation | Consistent blind spot. Better factor definition would fix it. |
| Purpose Limitation | 92% CFE flag rate | Overcalls -- definition is too broad, matches almost everything |
| Internal Security | 81% CFE flag rate | Same overcalling pattern |

---

## Decision Tree Root Cause: Consent

Deep-dive into consent factor routing:
- **FEATURE_FLAGS mismatch: 55%** -- the DT asks about feature flags that don't map to consent
- **COULD_NOT_EVALUATE -> NO_OPINION: 43%** -- "I don't know" routes as "not applicable"

The system treats uncertainty as absence. CFE's fix: INSUFFICIENT_EVIDENCE as a distinct third state.

---

## Escalation Rate

**9.7%** of reviews (32 out of 323) have active compliance risk warranting escalation.

---

## OOS Exclusion Accuracy

Out-of-scope exclusion error rate: **15% mean** (85% accuracy). The system incorrectly excludes 15% of requirements it marks as out-of-scope.

Remediation reviews (follow-ups to earlier reviews) cluster at **50% OOS accuracy** -- inherited parent scoping mismatch.

---

## SIN Prevention

**9/9 prevention rate** in pilot. CFE identified context gaps before SIN (Specialized Input Needed) reviews were triggered. All 9 cases where CFE flagged insufficient context would have required SIN review under current process.

---

## Overcalling Patterns

CFE overcalls broad factors. Top overcallers:
- purpose_limitation: 92% flag rate
- internal_security: 81% flag rate

These are real signals but low-specificity. The factor definitions are vague enough to match almost any project that handles user data. This is a precision tuning issue, not an architecture problem.

---

## Four Evaluation Modes (MRG Research)

Tested how knowledge representation affects LLM reasoning quality:

1. **Unstructured** -- raw text input, no schema
2. **Semi-structured** -- some field enforcement
3. **Fully structured** -- complete schema with vocabulary constraints
4. **Graph-aware** -- structured + relational context (entity maps, cross-references)

All four modes converge on structural findings. Graph-aware uniquely surfaces jurisdiction gaps that other modes miss.

---

## Taxonomy-Intuition Tension

Predefined categories (the 29-factor taxonomy) improve precision but constrain discovery. When CFE evaluates, it can only flag factors in the taxonomy. But real projects sometimes have risks that don't fit existing categories.

Possible solution: two-agent split:
- **Discoverer agent** (unconstrained) -- what risks do you see?
- **Evaluator agent** (constrained) -- which of the 29 factors apply?

The gap between what the Discoverer sees and what the Evaluator can name is where new factors are born. Like the DSM: clinical categories for diagnosis, clinical judgment for what falls outside.

---

## Youth Population Finding

292 youth-related requirements scattered across every category. The system applies them inconsistently. Reviews flagged as youth-relevant sometimes have 0 youth requirements applied.

---

## Error Taxonomy (Co-authored with Matt)

CFE provides real examples for:
- **Fabrication** -- evidence that doesn't exist in source data
- **Confabulation** -- evidence that sounds plausible but wasn't in input
- **Conflation** -- mixing up two different requirements or factors
- **System-level sycophancy** -- agreeing with the system's answer instead of evaluating independently

REDLINE's claim decomposition could solve CFE's overcalling problem -- but only after the taxonomy stabilizes.
