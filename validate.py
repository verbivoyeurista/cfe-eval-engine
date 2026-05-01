"""Run basic validation checks over `data/gathered` and `data/evaluated`."""
from pathlib import Path
import json


def validate_gathered(path: Path):
    for p in sorted(path.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(p, "-> invalid JSON:", e)


def main():
    root = Path(__file__).parent
    gathered = root / "data" / "gathered"
    evaluated = root / "data" / "evaluated"

    print("Validating gathered files...")
    if gathered.exists():
        validate_gathered(gathered)
    else:
        print("No gathered data found.")

    print("Validating evaluated files...")
    if evaluated.exists():
        validate_gathered(evaluated)
    else:
        print("No evaluated data found.")


if __name__ == "__main__":
    main()
