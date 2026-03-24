import firebase_admin
from firebase_admin import credentials, firestore, messaging
import pandas as pd
from datetime import datetime, timedelta
import os


# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase with service account credentials"""
    try:
        # Check if already initialized
        firebase_admin.get_app()
    except ValueError:
        # Initialize with service account key
        # Download from Firebase Console > Project Settings > Service Accounts
        cred_path = os.getenv('FIREBASE_CREDENTIALS', 'firebase-creds.json')

        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            print("⚠️ Firebase credentials not found!")
            print(f"   Looking for: {os.path.abspath(cred_path)}")
            print("   Please download from Firebase Console > Project Settings > Service Accounts")
            return False
    return True

# Initialize on import
_firebase_initialized = initialize_firebase()
if not _firebase_initialized:
    print("❌ Firebase initialization failed - check credentials file")

# Get Firestore client (only if initialized)
db = firestore.client() if _firebase_initialized else None

# ==========================================
# DATABASE FUNCTIONS
# ==========================================

def save_sensor_data(plant_id, temperature, humidity, soil_moisture, prediction):
    """Save sensor reading to Firestore"""
    try:
        doc_ref = db.collection('plants').document(plant_id).collection('sensor_data').document()
        doc_ref.set({
            'temperature': float(temperature),
            'humidity': float(humidity),
            'soil_moisture': float(soil_moisture),
            'prediction': prediction,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error saving sensor data: {e}")
        return None

def get_recent_sensor_data(plant_id, limit=100):
    """Get recent sensor readings for predictions"""
    try:
        readings = db.collection('plants').document(plant_id).collection('sensor_data')\
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                    .limit(limit).get()

        data = []
        for doc in readings:
            doc_data = doc.to_dict()
            data.append({
                'temperature': doc_data.get('temperature'),
                'humidity': doc_data.get('humidity'),
                'soil_moisture': doc_data.get('soil_moisture'),
                'plant_health': doc_data.get('prediction'),
                'timestamp': doc_data.get('timestamp')
            })
        return data
    except Exception as e:
        print(f"Error fetching sensor data: {e}")
        return []

def get_sensor_data_for_training(plant_id, days=30):
    """Get historical data for model retraining"""
    try:
        # Get data from last N days
        start_date = datetime.now() - timedelta(days=days)

        readings = db.collection('plants').document(plant_id).collection('sensor_data')\
                    .where('timestamp', '>=', start_date)\
                    .order_by('timestamp').get()

        data = []
        for doc in readings:
            doc_data = doc.to_dict()
            data.append({
                'temperature': doc_data.get('temperature'),
                'humidity': doc_data.get('humidity'),
                'soil_moisture': doc_data.get('soil_moisture'),
                'plant_health': doc_data.get('prediction')
            })

        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching training data: {e}")
        return pd.DataFrame()

# ==========================================
# NOTIFICATION FUNCTIONS
# ==========================================

def send_plant_alert(plant_id, condition, sensor_data):
    """Send notification for plant health alerts"""
    try:
        title = f"🌱 Plant Alert - {condition}"
        body = f"Temperature: {sensor_data['temperature']}°C, " \
               f"Humidity: {sensor_data['humidity']}%, " \
               f"Soil: {sensor_data['soil_moisture']}%"

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            topic=f"plant_{plant_id}_alerts"  # Subscribe devices to this topic
        )

        # Send the message
        response = messaging.send(message)
        print(f"Alert sent successfully: {response}")

        # Also save alert to database
        save_alert_to_db(plant_id, condition, body)

        return True
    except Exception as e:
        print(f"Error sending alert: {e}")
        return False

def save_alert_to_db(plant_id, alert_type, message):
    """Save alert to database for history"""
    try:
        doc_ref = db.collection('plants').document(plant_id).collection('alerts').document()
        doc_ref.set({
            'type': alert_type,
            'message': message,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'read': False
        })
        return doc_ref.id
    except Exception as e:
        print(f"Error saving alert: {e}")
        return None

def get_unread_alerts(plant_id):
    """Get unread alerts for dashboard display"""
    try:
        alerts = db.collection('plants').document(plant_id).collection('alerts')\
                  .where('read', '==', False)\
                  .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                  .get()

        return [alert.to_dict() for alert in alerts]
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return []

def mark_alerts_read(plant_id, alert_ids):
    """Mark alerts as read"""
    try:
        batch = db.batch()
        for alert_id in alert_ids:
            alert_ref = db.collection('plants').document(plant_id).collection('alerts').document(alert_id)
            batch.update(alert_ref, {'read': True})
        batch.commit()
        return True
    except Exception as e:
        print(f"Error marking alerts read: {e}")
        return False

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_plant_stats(plant_id):
    """Get statistics for dashboard"""
    try:
        # Get last 24 hours of data
        yesterday = datetime.now() - timedelta(days=1)

        readings = db.collection('plants').document(plant_id).collection('sensor_data')\
                    .where('timestamp', '>=', yesterday)\
                    .get()

        if not readings:
            return {}

        temps = [r.to_dict()['temperature'] for r in readings if 'temperature' in r.to_dict()]
        humidities = [r.to_dict()['humidity'] for r in readings if 'humidity' in r.to_dict()]
        soils = [r.to_dict()['soil_moisture'] for r in readings if 'soil_moisture' in r.to_dict()]

        return {
            'total_readings': len(readings),
            'avg_temperature': sum(temps) / len(temps) if temps else 0,
            'avg_humidity': sum(humidities) / len(humidities) if humidities else 0,
            'avg_soil_moisture': sum(soils) / len(soils) if soils else 0,
            'last_reading': readings[0].to_dict() if readings else None
        }
    except Exception as e:
        print(f"Error getting plant stats: {e}")
        return {}