"""Quick test to check if data exists in Firebase Firestore"""
from firebase import db, _firebase_initialized

if not _firebase_initialized:
    print("❌ Firebase not initialized - check your credentials file")
    exit(1)

print("🔍 Checking Firestore for stored data...\n")

# Check sensor_data
sensor_docs = db.collection('plants').document('plant_001').collection('sensor_data').limit(5).get()
print(f"📊 sensor_data collection: {len(sensor_docs)} record(s) found")
for doc in sensor_docs:
    data = doc.to_dict()
    print(f"   ID: {doc.id}")
    print(f"   🌡 Temp: {data.get('temperature')}°C | 💧 Humidity: {data.get('humidity')}% | 🌱 Soil: {data.get('soil_moisture')}%")
    print(f"   Prediction: {data.get('prediction')} | Time: {data.get('timestamp')}")
    print()

# Check alerts
alert_docs = db.collection('plants').document('plant_001').collection('alerts').limit(5).get()
print(f"🚨 alerts collection: {len(alert_docs)} record(s) found")
for doc in alert_docs:
    data = doc.to_dict()
    print(f"   {data.get('type')}: {data.get('message')}")

if len(sensor_docs) == 0 and len(alert_docs) == 0:
    print("\n⚠️ No data found yet! Run data_logger.py to start collecting data from your ESP32.")
else:
    print("\n✅ Data is being stored successfully in Firebase Firestore!")
