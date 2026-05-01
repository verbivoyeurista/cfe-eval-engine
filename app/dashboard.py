from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT.parent / "data"


def main():
    st.title("cfe-eval-engine: Dashboard")

    runs_dir = DATA_DIR / "runs"
    if not runs_dir.exists():
        st.info("No runs found in data/runs. Add run JSON files to visualize.")
        return

    runs = sorted(runs_dir.glob("**/*.json"))
    if not runs:
        st.info("No run files found in data/runs.")
        return

    st.subheader("Available runs")
    for r in runs:
        st.write(r.relative_to(DATA_DIR))


if __name__ == "__main__":
    main()
