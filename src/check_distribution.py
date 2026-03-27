import pandas as pd
from pathlib import Path

# ── Resolve CSV path relative to this file so it works from any CWD ──────────
BASE_DIR = Path(__file__).parent.parent  # project root
CSV_PATH = BASE_DIR / "soil_dataa.csv"

df = pd.read_csv(CSV_PATH)

# Check class distribution
print("Class Distribution:\n")
print(df['plant_health'].value_counts())
print(f"\nTotal rows: {len(df)}")