import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle
from firebase import get_sensor_data_for_training

# ── Resolve paths relative to this file so it works from any CWD ──────────────
BASE_DIR = Path(__file__).parent.parent  # project root
CSV_PATH = BASE_DIR / "soil_dataa.csv"

# 1. Load dataset from Firebase instead of CSV
print("📥 Loading training data from Firebase...")
data = get_sensor_data_for_training("plant_001", days=30)  # Last 30 days

if data.empty:
    print("❌ No data found in Firebase. Using backup CSV file...")
    try:
        data = pd.read_csv(CSV_PATH)
        print(f"✅ Loaded backup data from {CSV_PATH.name}")
    except FileNotFoundError:
        print(f"❌ No training data available! Expected at: {CSV_PATH}")
        exit(1)

print(f"📊 Loaded {len(data)} training samples")
print(data.head())

# 2. Features & Labels
X = data[['temperature', 'humidity', 'soil_moisture']]
y = data['plant_health']

# 3. Feature Scaling
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 4. Train-Test Split (stratified = balanced split)
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y)

# 5. Models
models = {
    "Decision Tree": DecisionTreeClassifier(max_depth=5),
    "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=7)
}

best_model = None
best_accuracy = 0

# 6. Train and Compare
for name, model in models.items():
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    acc = accuracy_score(y_test, predictions)

    print(f"\n{name} Accuracy: {acc:.4f}")
    print("Classification Report:")
    print(classification_report(y_test, predictions))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    if acc > best_accuracy:
        best_accuracy = acc
        best_model = model

# 7. Save Model to project root
pickle.dump(best_model, open(BASE_DIR / "model.pkl", "wb"))
pickle.dump(scaler, open(BASE_DIR / "scaler.pkl", "wb"))

print(f"\n✅ Best model ({type(best_model).__name__}, accuracy={best_accuracy:.4f}) saved to project root!")