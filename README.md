# Streamlit JSON Dashboard

Minimal Streamlit app that reads JSON files from the `data/` folder and displays them with `pandas` and `plotly`.

## Requirements
- Python 3.8+
- Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Project layout
- `app.py` - main Streamlit app
- `data/` - place your JSON files here (sample files included)
- `requirements.txt` - Python dependencies
- `start.sh` - convenience script to run the app

## GitHub
To create a remote GitHub repository and push:

```bash
# create repo locally (already done)
git remote add origin git@github.com:<your-username>/<repo>.git
git push -u origin main

# or use GitHub CLI:
gh repo create <your-username>/<repo> --public --source=. --remote=origin
git push -u origin main
```

If you want, I can create the remote for you with the GitHub CLI (`gh`) if it's installed and you authorize it.
