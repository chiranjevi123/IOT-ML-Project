import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")


# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase with service account credentials"""
    try:
        # Check if already initialized
        firebase_admin.get_app()
    except ValueError:
        # Look for credentials relative to this file's location, then CWD
        cred_path = os.getenv('FIREBASE_CREDENTIALS', 'firebase-creds.json')

        # Also search one level up (project root) if not found in CWD
        if not os.path.exists(cred_path):
            parent_path = os.path.join(os.path.dirname(__file__), '..', cred_path)
            if os.path.exists(parent_path):
                cred_path = parent_path

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
    if db is None:
        print("❌ Firebase not initialized - cannot save sensor data")
        return None
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
    if db is None:
        return []
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
    if db is None:
        return pd.DataFrame()
    try:
        # Get data from last N days
        start_date = datetime.now() - timedelta(days=days)

        # Note: where + order_by on different fields requires a composite index in Firestore.
        # We fetch ordered by timestamp and filter in Python to avoid index errors.
        readings = db.collection('plants').document(plant_id).collection('sensor_data')\
                    .order_by('timestamp').get()

        data = []
        for doc in readings:
            doc_data = doc.to_dict()
            ts = doc_data.get('timestamp')
            # Filter by date in Python to avoid composite index requirement
            if ts and hasattr(ts, 'replace'):
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                if ts_naive < start_date:
                    continue
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
    """Send email notification for plant health alerts via Gmail SMTP"""
    sender   = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")   # Gmail App Password
    receiver = os.getenv("EMAIL_RECEIVER")

    if not all([sender, password, receiver]):
        print("⚠️ Email not configured — set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER in .env")
        # Still save alert to Firestore even if email is not configured
        body = (f"Temperature: {sensor_data['temperature']}°C, "
                f"Humidity: {sensor_data['humidity']}%, "
                f"Soil: {sensor_data['soil_moisture']}%")
        save_alert_to_db(plant_id, condition, body)
        return False

    temp  = sensor_data['temperature']
    hum   = sensor_data['humidity']
    soil  = sensor_data['soil_moisture']

    subject = f"🌱 Plant Alert — {condition} Condition Detected"

    html_body = f"""\
    <html><body style="font-family: Arial, sans-serif; padding: 20px;">
      <h2 style="color:#e74c3c;">🌿 Plant Health Alert</h2>
      <p>Your plant (<b>{plant_id}</b>) has been detected as <b style="color:#e74c3c;">{condition}</b>.</p>
      <table style="border-collapse:collapse; width:300px;">
        <tr><th style="background:#f2f2f2;padding:8px;text-align:left;">Sensor</th>
            <th style="background:#f2f2f2;padding:8px;text-align:left;">Value</th></tr>
        <tr><td style="padding:8px;">🌡️ Temperature</td><td style="padding:8px;">{temp}°C</td></tr>
        <tr><td style="padding:8px;">💧 Humidity</td>   <td style="padding:8px;">{hum}%</td></tr>
        <tr><td style="padding:8px;">🌱 Soil Moisture</td><td style="padding:8px;">{soil}%</td></tr>
      </table>
      <p style="margin-top:16px;">Please check on your plant and take action as needed.</p>
      <hr/><small>Sent by IoT Plant Monitor</small>
    </body></html>
    """

    plain_body = (f"Plant Alert — {condition}\n"
                  f"Temperature: {temp}°C | Humidity: {hum}% | Soil: {soil}%\n"
                  f"Please check on your plant.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.sendmail(sender, receiver, msg.as_string())
        print(f"📧 Alert email sent to {receiver}")

        # Save to Firestore for dashboard display
        save_alert_to_db(plant_id, condition, plain_body)
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail authentication failed — make sure you are using an App Password, not your regular password.")
        print("   Guide: https://support.google.com/accounts/answer/185833")
        save_alert_to_db(plant_id, condition, plain_body)
        return False
    except Exception as e:
        print(f"❌ Failed to send alert email: {e}")
        save_alert_to_db(plant_id, condition, plain_body)
        return False


def save_alert_to_db(plant_id, alert_type, message):
    """Save alert to database for history"""
    if db is None:
        return None
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
    if db is None:
        return []
    try:
        # Fetch unread alerts - order_by after where requires a composite index,
        # so we fetch all unread and sort in Python.
        alerts = db.collection('plants').document(plant_id).collection('alerts')\
                  .where('read', '==', False)\
                  .get()

        result = []
        for alert in alerts:
            # IMPORTANT: include the document ID so mark_alerts_read can work
            data = alert.to_dict()
            data['id'] = alert.id
            result.append(data)

        # Sort by timestamp descending in Python
        result.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)
        return result
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return []


def mark_alerts_read(plant_id, alert_ids):
    """Mark alerts as read"""
    if db is None:
        return False
    try:
        batch = db.batch()
        for alert_id in alert_ids:
            if not alert_id:
                continue
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
    if db is None:
        return {}
    try:
        # Get last 24 hours of data
        yesterday = datetime.now() - timedelta(days=1)

        # Fetch all recent data ordered by timestamp; filter in Python
        # to avoid composite index requirement (where + order_by different fields)
        readings = db.collection('plants').document(plant_id).collection('sensor_data')\
                    .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                    .limit(500)\
                    .get()

        filtered = []
        for r in readings:
            doc_data = r.to_dict()
            ts = doc_data.get('timestamp')
            if ts and hasattr(ts, 'replace'):
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                if ts_naive >= yesterday:
                    filtered.append(doc_data)

        if not filtered:
            return {}

        temps = [r['temperature'] for r in filtered if 'temperature' in r]
        humidities = [r['humidity'] for r in filtered if 'humidity' in r]
        soils = [r['soil_moisture'] for r in filtered if 'soil_moisture' in r]

        return {
            'total_readings': len(filtered),
            'avg_temperature': sum(temps) / len(temps) if temps else 0,
            'avg_humidity': sum(humidities) / len(humidities) if humidities else 0,
            'avg_soil_moisture': sum(soils) / len(soils) if soils else 0,
            'last_reading': filtered[0] if filtered else None
        }
    except Exception as e:
        print(f"Error getting plant stats: {e}")
        return {}