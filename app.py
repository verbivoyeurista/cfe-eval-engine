import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"


@st.cache_data
def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_dataframe(obj):
    if isinstance(obj, list):
        try:
            return pd.json_normalize(obj)
        except Exception:
            return pd.DataFrame(obj)
    if isinstance(obj, dict):
        try:
            return pd.json_normalize(obj)
        except Exception:
            return pd.DataFrame([obj])
    return pd.DataFrame({"value": [obj]})


def main():
    st.title("Streamlit JSON Dashboard")

    DATA_DIR.mkdir(exist_ok=True)
    files = sorted(DATA_DIR.glob("*.json"))

    if not files:
        st.warning(f"No JSON files found in {DATA_DIR}. Add files to the data folder.")
        return

    file_choice = st.selectbox("Select JSON file", options=[f.name for f in files])
    path = DATA_DIR / file_choice
    data = load_json(path)

    st.subheader("Raw JSON")
    st.code(json.dumps(data, indent=2), language="json")

    df = to_dataframe(data)
    st.subheader("Table view")
    st.dataframe(df)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        st.subheader("Charts")
        y_col = st.selectbox("Choose numeric column", numeric_cols)

        # try to detect a time column
        time_cols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
        if time_cols:
            x_col = time_cols[0]
            try:
                df[x_col] = pd.to_datetime(df[x_col])
                fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            except Exception:
                fig = px.histogram(df, x=y_col, nbins=30, title=y_col)
        else:
            fig = px.histogram(df, x=y_col, nbins=30, title=y_col)

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns detected for charting.")


if __name__ == "__main__":
    main()
