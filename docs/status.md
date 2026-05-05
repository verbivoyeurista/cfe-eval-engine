# Project Status — May 2026

## Where Things Stand

The evaluation pipeline is complete and validated. The corpus is large enough to be statistically meaningful. The methodology has been tested blind against expert ground truth and holds up (89-92% review-level recall).

What's left is packaging: get the Streamlit app running, write the research paper, and build portfolio pieces.

## Immediate Next Steps

### 1. Streamlit App (This Week)

The dashboard (`app/dashboard.py`) is ready to run. Steps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app/dashboard.py
```

It loads runs from `data/runs/` (150+ scored JSONs). Four pages:
- **Corpus Overview** -- top-level metrics, verdict distribution, coverage gaps
- **Review Explorer** -- drill into any review, see factor-by-factor CFE vs system comparison
- **Taxonomy Health** -- factor application rates, graduation pipeline, under-scoping by factor
- **Methodology** -- the three-tier framework explanation

After it runs locally:
- Fix any import/path issues
- Add a validation page (show precision/recall/F1 from validate.py output)
- Deploy to Streamlit Cloud (free tier, public URL for portfolio)

### 2. Methodology Write-Up (Portfolio Centerpiece)

`docs/methodology.md` is written. Needs to be polished into a standalone document framed as eval engineering:
- What problem does CFE solve?
- How does the pipeline work?
- What design decisions were made and why?
- What did the validation show?

Frame it for eval engineer / AI safety hiring managers. Emphasize: structured evaluation methodology, information separation to prevent confirmation bias, three-valued logic, bottom-up taxonomy design, evidence grounding.

### 3. Classifier Experiment (ML Portfolio Piece)

Train a classifier on CFE data: predict which risk factors apply from intake text alone. This demonstrates ML capability beyond the evaluation work.

Plan:
- Start with logistic regression (baseline)
- Try a simple neural net
- Evaluate precision/recall by factor
- Write up as an experiment (hypothesis, method, results, what you learned)

### 4. Research Paper (Ongoing)

Co-authoring error taxonomy paper with Matt. CFE provides real examples for fabrication, confabulation, conflation, and system-level sycophancy.

## Data Assets

Everything in `data/` is the corpus. Most important:

| Directory | Count | What |
|-----------|-------|------|
| `data/gathered/` | ~280 | Raw review data (intake, requirements, entity maps) |
| `data/evaluated/` | ~150 | Independent CFE evaluations (before seeing system answer) |
| `data/runs/` | ~150 | Final scored runs (merged, verdicts, grounding checks) |
| `data/validation/` | 10 | Ground truth validation results + case studies |

**Important**: `.gitignore` excludes `gathered/`, `evaluated/`, and `runs/` JSONs. If you push to GitHub, the data won't be included. Save the data separately (zip to personal storage).

## Timeline Context

Brittney is targeting Eval Engineer / Applied AI Safety roles. The work here IS the portfolio:
- CFE methodology = eval engineering
- 494-review pipeline = scale
- Bottom-up taxonomy = research methodology
- Validation results = rigor
- Schema evolution = iteration discipline

The content design background + eval methodology + ML basics = a rare combination for eval roles.

## What's NOT in This Repo

- The original data gathering scripts (used internal company APIs)
- The GraphQL queries (company-specific)
- The MetaMate/MyClaw agent prompts (Gus, the sibling agent)
- The demo HTML files (PixelCloud hosted, not in repo)
- The full 494 runs (this repo has the ~150 that went through the full pipeline)

Everything needed to understand the methodology, run the dashboard, and validate results IS here.
