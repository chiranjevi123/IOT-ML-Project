"""Upload soil_dataa.csv to Firebase Firestore as initial data"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from firebase import db, _firebase_initialized

if not _firebase_initialized or db is None:
    print("❌ Firebase not initialized - check credentials")
    exit(1)

# ── Resolve CSV path relative to this file so it works from any CWD ──────────
BASE_DIR = Path(__file__).parent.parent  # project root
CSV_PATH = BASE_DIR / "soil_dataa.csv"

# Load CSV
df = pd.read_csv(CSV_PATH)
print(f"📂 Loaded {len(df)} rows from {CSV_PATH.name}")
print(f"   Columns: {list(df.columns)}")
print(f"   Health labels: {df['plant_health'].value_counts().to_dict()}")
print()

PLANT_ID = "plant_001"
collection_ref = db.collection('plants').document(PLANT_ID).collection('sensor_data')

# Upload in batches of 450 (Firestore batch limit is 500)
BATCH_SIZE = 450
total_uploaded = 0

for start in range(0, len(df), BATCH_SIZE):
    batch = db.batch()
    chunk = df.iloc[start:start + BATCH_SIZE]

    for _, row in chunk.iterrows():
        doc_ref = collection_ref.document()  # auto-generate ID

        # Parse timestamp from CSV
        try:
            ts = datetime.strptime(str(row['timestamp']), '%m/%d/%Y %H:%M:%S')
        except (ValueError, KeyError):
            ts = datetime.now()

        batch.set(doc_ref, {
            'temperature': float(row['temperature']),
            'humidity': float(row['humidity']),
            'soil_moisture': float(row['soil_moisture']),
            'prediction': str(row['plant_health']),
            'timestamp': ts
        })

    batch.commit()
    total_uploaded += len(chunk)
    print(f"   ✅ Uploaded batch: {total_uploaded}/{len(df)} records")

print(f"\n🎉 Done! {total_uploaded} records uploaded to Firestore")
print(f"   📍 Path: plants/{PLANT_ID}/sensor_data")
