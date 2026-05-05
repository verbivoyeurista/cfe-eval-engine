# CFE Methodology

## What CFE Evaluates

CFE measures how well a privacy review system catches risk. A "privacy review" is the process a tech company uses to assess whether a new product or feature handles user data correctly. The system attaches risk factors (like "consent" or "data retention") to a project, then routes requirements based on those factors.

The question isn't "is the product safe?" The question is "did the review system do its job?"

## The Problem

Privacy review systems use decision trees (DTs) to decide which risk factors apply to a project. The DT asks questions about the project, and based on the answers, attaches or excludes risk factors. Each attached factor brings a set of compliance requirements.

The problem: DTs are brittle. They ask the wrong questions, in the wrong order, with insufficient options. When a DT can't evaluate a factor, the system maps "I don't know" to "not applicable." This is the core flaw.

**99.56% of under-scoping is a routing gap -- the system never asked the right question -- not an assessor error.**

## How CFE Works

### Step 1: Gather

Pull everything about a review:
- Intake data (what the project does, who it affects, what data it uses)
- All compliance requirements with full text
- System's risk factor attachments
- Decision tree responses (what the system asked and what was answered)

Extract an **entity map** from the intake: users, data types, models, surfaces, features, data flows. This structured representation of "what the project actually does" is what drives evaluation.

### Step 2: Evaluate (Independent)

An evaluator agent reads the project context and the 29-factor taxonomy. For each factor, it independently decides: does this factor apply?

Three possible answers:
- **IN_SCOPE** -- this factor applies to this project
- **OUT_OF_SCOPE** -- this factor does not apply
- **INSUFFICIENT_EVIDENCE** -- can't tell from available information (NOT the same as "no")

The evaluator NEVER sees the system's answer. This separation prevents confirmation bias. The evaluator commits before seeing what the system said.

Every evaluation includes:
- **Reasoning** -- why this factor applies or doesn't
- **Evidence** -- specific data from the project context (not world knowledge)
- **Provenance** -- which field in the gathered data the evidence came from
- **Reasoning context** -- what was considered, what was uncertain, what would change the call

### Step 3: Compare

Merge the evaluator's independent judgment with the system's actual decisions. For each factor:
- **AGREE** -- both CFE and system say the same thing
- **DISAGREE** -- they differ (this is where the signal is)
- **UNDETERMINED** -- system didn't evaluate, or CFE had insufficient evidence

### Step 4: Score

Three scores, three shapes:

**Accuracy** (established risk, 14 factors): correct / applicable. A ratio. How often did the system get it right on factors it's supposed to track? Denominator is established factors that have requirements in the system.

**Coverage** (emergent risk, 10 factors): prioritized gap list. Not a ratio. Which emerging risks does CFE flag that the system doesn't track at all? These are discovery outputs for system expansion.

**Readiness** (projected risk, 5 factors): prioritized exposure list. Not a ratio. Which regulatory requirements are coming that the system isn't prepared for?

### Step 5: Verdict

Driven by Accuracy and Coverage (Readiness is informational):
- **NO_ESCALATION** -- system performed correctly, no gaps
- **UNDER_SCOPED** -- system missed established factors
- **NEEDS_MORE_INFO** -- insufficient data to assess

### Step 6: Ground Check

Evidence grounding verification. For each factor evaluation, check whether the evidence string can be traced back to the gathered input data. Catches:
- **Fabrication** -- evidence that doesn't exist in the source data
- **Confabulation** -- evidence that sounds plausible but wasn't in the input

Uses provenance pointers (direct path) when available, fuzzy word matching as fallback.

---

## The Taxonomy

29 risk factors organized into three tiers. Derived bottom-up from:
- 1,401 system requirements (corpus-mined)
- LLM-surfaced signals from evaluation runs
- Regulatory frameworks (EU AI Act, GDPR, DSA, DPDP, PIPL, KOSA, AADC)

### Factor Lifecycle

```
observed -> emerging -> recommended -> established
```

No factor enters the scored taxonomy without evidence:
- **Observed**: appeared in an evaluation
- **Emerging**: 5+ unique reviews
- **Recommended**: 25+ reviews with evidence package (proposed requirement text + implementation steps)
- **Established**: system has built dedicated requirements and a category

### Bias Control

10 simple reviews tested as negative controls. 80 emergent factor evaluations. **0 false positives.** The emergent factors discriminate based on review content, not reflexively.

---

## Schema Evolution

### v1: No constraints
LLM freestyled everything. Factor names inconsistent, evidence unverifiable, scores not comparable across runs.

### v2: Structure imposed
Schema enforcement, requirement text validation, 20 factors. Quality gates that reject malformed runs. This version produced the first comparable corpus.

### v3: Vocabulary locked
Input data preservation (keep everything the gatherer found), vocabulary constraints (only canonical factor IDs), 29 factors (added emergent and projected tiers).

### v3.1: Information separation
The evaluator no longer sees system_says. Three-tier scoring replaces single accuracy number. Population flags (youth). Evidence packages with provenance. Grounding checks.

Each version was informed by what broke in the previous one. The iteration story is important -- it shows how the methodology was refined through empirical failure, not designed in advance.

---

## Validation

### Against Expert Ground Truth (152 runs)
- All 152 runs evaluated blind and scored
- Three-way comparison: CFE vs Forest vs SME ground truth
- **Review-level recall: 89-92%**
- One miss: L1418370PRV2 -- methodology disagreement ("always attach" rule vs context evaluation)
- protected_characteristics: 0% recall -- consistent blind spot, fixable with better factor definition

### Against Audit Failures
- 812 audit failures analyzed
- CFE validation framework: precision, recall, F1 per factor
- Maps audit risk factor names to CFE factor IDs (many-to-many)

### Overcalling Analysis
CFE overcalls broad factors (purpose_limitation 92%, internal_security 81%). This is a precision problem, not an architecture problem. These factors have vague definitions that match almost any project.

---

## Key Insight: Entity Maps vs Requirement Text

An accidental controlled experiment: 72% of requirement text was null due to a data bug. CFE Run 4 still produced highly specific findings -- more specific than DTs or Forest.

**Hypothesis**: Entity maps (structured representation of users, data, models, surfaces, features, data flows) may drive scoping decisions more than requirement text. Requirement text may matter more for evaluation depth (what does this requirement actually require?) than for scoping (should this factor apply?).

This is still a hypothesis. The comparison study hasn't been run yet.

---

## Population Flags

Youth is the only population flag. It exists because:
- Bright legal line (under 13/16/18)
- Dedicated Risk Area
- 292 requirements scattered across every category

The flag checks whether the system applied youth-related requirements, not which age band applies. Age-band filtering is the requirement layer's job.

---

## What Makes CFE Different

1. **Context-first, not tree-first.** Characterize the project, then evaluate. Don't force the project through a decision tree's narrow questions.

2. **Three-valued logic.** IN_SCOPE, OUT_OF_SCOPE, INSUFFICIENT_EVIDENCE. The third value is the architectural innovation -- "I don't know" is not "no."

3. **Independent evaluation.** The evaluator never sees the system's answer. This catches blind spots the system will never find on its own.

4. **Structured evidence.** Every call has reasoning, evidence, provenance, and an audit trail. Not just a label.

5. **Bottom-up taxonomy.** Factors emerged from data, not from a committee. The lifecycle ensures factors earn their way into the scored set.

6. **Multiple output shapes.** Accuracy is a ratio for auditors. Coverage is a list for system owners. Readiness is a list for policy. Same data, different views for different audiences.
