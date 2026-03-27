import requests
import time
from datetime import datetime
from firebase import save_sensor_data, send_plant_alert

# 🔴 CHANGE THIS TO YOUR ESP32 IP
ESP_URL = "http://192.168.1.12/data"

# Plant ID for Firebase
PLANT_ID = "plant_001"

print("🚀 Collecting sensor data via WiFi...")
print("Data will be saved to Firebase & notifications sent for alerts")
print("=" * 80)

def label_data(temp, humidity, soil):
    """Improved labeling logic"""

    # 🔴 Critical conditions → Unhealthy
    if soil < 30 or temp > 38 or temp < 10:
        return "Unhealthy"
    # 🟡 Moderate stress
    if (30 <= soil < 60) or (humidity < 40):
        return "Moderate"
    else:
        return "Healthy"

try:
    while True:
        try:
            response = requests.get(ESP_URL, timeout=5)
            sensor = response.json()

            temp = float(sensor["temp"])
            humidity = float(sensor["humidity"])
            soil = float(sensor["soil"])

            # ✅ Noise filtering
            if not (0 <= temp <= 60 and 0 <= humidity <= 100 and 0 <= soil <= 100):
                continue

            label = label_data(temp, humidity, soil)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 🔥 SAVE TO FIREBASE INSTEAD OF CSV
            doc_id = save_sensor_data(PLANT_ID, temp, humidity, soil, label)

            if doc_id:
                print(f"[{timestamp}] ✅ Saved to Firebase (ID: {doc_id[:8]}...)")
                print(f"   🌡 {temp}°C | 💧 {humidity}% | 🌱 {soil}% → {label}")

                # 🚨 SEND ALERT FOR UNHEALTHY CONDITIONS
                if label == "Unhealthy":
                    sensor_data = {
                        'temperature': temp,
                        'humidity': humidity,
                        'soil_moisture': soil
                    }
                    send_plant_alert(PLANT_ID, "Unhealthy", sensor_data)
                    print("   🚨 Alert notification sent!")
            else:
                print(f"[{timestamp}] ❌ Failed to save to Firebase")

            time.sleep(3)  # sync with ESP32

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)

except KeyboardInterrupt:
    print("\n" + "=" * 80)
    print("🛑 Data collection stopped")
    print("📊 Data has been saved to Firebase database")
    print("🚨 Alerts sent for unhealthy conditions")
    print("=" * 80)