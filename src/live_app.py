import streamlit as st
import pickle
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd
from firebase import (get_recent_sensor_data, get_unread_alerts, mark_alerts_read,
                      get_plant_stats, save_sensor_data, send_plant_alert, save_alert_to_db)
from ai_advisor import get_plant_advice

import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# ── Resolve paths relative to this file so it works from any CWD ──────────────
BASE_DIR = Path(__file__).parent.parent  # project root

# ----------- Configuration -----------
DEFAULT_PORT = 'COM8'   # Linux default; change to COM8 on Windows
DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 1

# ✅ ADD YOUR ESP32 IP HERE
ESP_URL = "http://192.168.1.19/data"   # CHANGE THIS to your ESP32 IP

# Firebase Plant ID``
PLANT_ID = "plant_001"

# ----------- Email Alert Configuration -----------
SENDER_EMAIL = "devap6622@gmail.com"       #  Change to your Gmail
APP_PASSWORD = "doyr ypey ubis ebtc"          # Change to your 16-char App Password
RECEIVER_EMAIL = "chiranjevidabbeti@gmail.com" # Change to receiver Gmail
ALERT_COOLDOWN = 60                         #  Seconds to wait before sending another email


def send_email_alert(priority, msg, temp, humidity, soil, prediction):
    """Sends an email alert using Gmail SMTP."""
    if APP_PASSWORD == "doyr ypey ubis ebtc" and SENDER_EMAIL != "devap6622@gmail.com":
         # Just a safety check; we will let it attempt to send anyway!
         pass

    try:
        subject = f"🚨 Plant Monitor Alert: {priority}"
        body = f"🌱 Plant Monitoring Alert system triggered!\n\n" \
               f"Priority: {priority}\n" \
               f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" \
               f"📊 Sensor Readings:\n" \
               f"- Temperature: {temp} °C\n" \
               f"- Humidity: {humidity} %\n" \
               f"- Soil Moisture: {soil} %\n" \
               f"- Model Prediction: {prediction}\n\n" \
               f"⚠️ Message: {msg}"
        
        msg_obj = MIMEMultipart()
        msg_obj['From'] = SENDER_EMAIL
        msg_obj['To'] = RECEIVER_EMAIL
        msg_obj['Subject'] = subject
        msg_obj.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg_obj)
        server.quit()
        print(f"Email alert sent successfully! Priority: {priority}")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

def generate_alert(temp, humidity, soil_moisture, prediction):
    """
    Evaluates sensor data and returns (Priority, Message).
    Logic derived from previous project recommendations logic.
    """
    # CRITICAL checks
    if soil_moisture < 20 or temp > 38 or temp < 12 or prediction == "Unhealthy":
        msg = f"Critical levels detected: Soil {soil_moisture}%, Temp {temp}°C. Action required!"
        return "CRITICAL", msg
    # WARNING checks
    elif soil_moisture < 40 or temp > 30 or humidity < 35 or humidity > 80:
        msg = f"Conditions sub-optimal: Soil {soil_moisture}%, Temp {temp}°C, Hum {humidity}%."
        return "WARNING", msg
    # NORMAL
    else:
        return "NORMAL", "Parameters are in safe range."


def parse_sensor_line(line):
    raw = line.strip()

    if not raw:
        return None, None

    blacklist_keywords = [
        'DHT', 'ERROR', 'ERR', 'GURU', 'EXCVADDR', 'BACKTRACE', 'PANIC', 'entry 0x', 'DEADBEEF'
    ]
    if any(tok in raw.upper() for tok in blacklist_keywords):
        return None, None

    if raw.upper().startswith('DATA,'):
        raw = raw[5:].strip()

    fields = raw.split(',')

    if len(fields) != 3 or raw.count(',') != 2:
        return None, f"Incomplete/invalid data: {fields}"

    try:
        temp = float(fields[0])
        humidity = float(fields[1])
        soil_moisture = float(fields[2])
    except ValueError as e:
        return None, f"Parse error: {e}"

    if not -20 <= temp <= 60:
        return None, f"Temperature out of range: {temp}"
    if not 0 <= humidity <= 100:
        return None, f"Humidity out of range: {humidity}"
    if not 0 <= soil_moisture <= 100:
        return None, f"Soil moisture out of range: {soil_moisture}"

    return {
        'temp': temp,
        'humidity': humidity,
        'soil_moisture': soil_moisture,
    }, None


def get_recommendation(temp, humidity, soil_moisture, model_prediction):
    recs = []
    if temp < 15:
        recs.append("🌡️ Temperature is low - avoid cold stress")
    elif temp > 35:
        recs.append("🔥 Temperature is high - provide shade")

    if humidity < 30:
        recs.append("💨 Humidity is low - mist or increase humidity")
    elif humidity > 80:
        recs.append("💧 Humidity is high - improve ventilation")

    if soil_moisture < 25:
        recs.append("💧 Soil is dry - water plant soon")
    elif soil_moisture > 70:
        recs.append("⛔ Soil is wet - skip watering / check drainage")

    recs.append(f"🤖 Model predicts: {model_prediction}")

    if len(recs) == 1:  # only the model prediction line
        recs.insert(0, "✅ All parameters are in nominal range.")
    return recs


st.set_page_config(page_title='Live IoT Plant Monitor', layout='wide', initial_sidebar_state='expanded')

st.title('🌱 IoT Live Plant Monitoring (ESP32)')
st.write('Use this dashboard with your ESP32 sensor stream. Click `Read Sensor` to fetch live data.')

with st.sidebar:
    st.header('Settings')
    auto_refresh = st.checkbox('Auto-refresh (until stopped)', value=False)
    interval = st.slider('Refresh interval (seconds)', 1, 10, value=2)

try:
    model = pickle.load(open(BASE_DIR / 'model.pkl', 'rb'))
    scaler = pickle.load(open(BASE_DIR / 'scaler.pkl', 'rb'))
except FileNotFoundError:
    st.error('❌ model.pkl or scaler.pkl not found. Run train_model.py first, then restart this app.')
    st.stop()

status_box = st.empty()
metrics_box = st.container()
log_box = st.expander('Raw log & debug output', expanded=False)

# ✅ Graph storage
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["time", "temp", "humidity", "soil"])

# ✅ Alert System storage
if "alert_history" not in st.session_state:
    st.session_state.alert_history = []
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = 0
if "last_alert_priority" not in st.session_state:
    st.session_state.last_alert_priority = "NORMAL"

def process_sensor_reading():
    try:
        response = requests.get(ESP_URL, timeout=2)
        data = response.json()

        # Build a clean 3-field line from WiFi JSON response
        line = f"{data['temp']},{data['humidity']},{data['soil']}"

    except Exception as e:
        status_box.error(f"⚠️ Connection error: {e}")
        return None

    parsed, err = parse_sensor_line(line)

    if err:
        status_box.warning(f'⚠️ Sensor parse failed: {err}')
        with log_box:
            st.write(f'{datetime.now()} - malformed line: {repr(line)}')
        return None

    if parsed is None:
        status_box.info('ℹ️ Waiting for valid sensor data...')
        return None

    # Store data for graphs
    new_row = {
        "time": datetime.now(),
        "temp": parsed['temp'],
        "humidity": parsed['humidity'],
        "soil": parsed['soil_moisture']
    }

    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])])
    st.session_state.df = st.session_state.df.tail(200)

    x = [[parsed['temp'], parsed['humidity'], parsed['soil_moisture']]]
    x_scaled = scaler.transform(x)
    prediction = model.predict(x_scaled)[0]

    # Save every reading to Firebase
    doc_id = save_sensor_data(PLANT_ID, parsed['temp'], parsed['humidity'],
                              parsed['soil_moisture'], prediction)
    if doc_id:
        firebase_status = f"✅ Saved to Firebase (ID: {doc_id[:8]}...)"
    else:
        firebase_status = "⚠️ Firebase save failed"

    # Send alert for unhealthy conditions (Firebase)
    if prediction == "Unhealthy":
        sensor_info = {
            'temperature': parsed['temp'],
            'humidity': parsed['humidity'],
            'soil_moisture': parsed['soil_moisture']
        }
        send_plant_alert(PLANT_ID, "Unhealthy", sensor_info)

    # ---------------- 🚨 Priority Alert Logic Integration ----------------
    priority, alert_msg = generate_alert(parsed['temp'], parsed['humidity'], parsed['soil_moisture'], prediction)
    
    current_time = time.time()
    send_email = False
    
    if priority != "NORMAL":
        time_since_last = current_time - st.session_state.last_alert_time
        
        # Smart Alert Logic: Avoid spam.
        # Send if priority is CRITICAL or if Priority Changed. Also respect Cooldown.
        if (priority == "CRITICAL" or priority != st.session_state.last_alert_priority) and time_since_last > ALERT_COOLDOWN:
            send_email = True
            
        if send_email:
            send_email_alert(priority, alert_msg, parsed['temp'], parsed['humidity'], parsed['soil_moisture'], prediction)
            st.session_state.last_alert_time = current_time
            st.session_state.last_alert_priority = priority

            # ✅ Persist alert to Firestore so it survives page refresh
            save_alert_to_db(PLANT_ID, priority, alert_msg)

            # Save to UI Alert History (Limit 10)
            alert_entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "priority": priority,
                "msg": alert_msg
            }
            st.session_state.alert_history.insert(0, alert_entry)
            st.session_state.alert_history = st.session_state.alert_history[:10]

    # Store latest reading in session_state for the AI advisor (rendered outside this fn)
    st.session_state["live_temp"] = parsed['temp']
    st.session_state["live_humidity"] = parsed['humidity']
    st.session_state["live_soil"] = parsed['soil_moisture']
    st.session_state["live_prediction"] = prediction
    st.session_state["live_ai_advice"] = st.session_state.get("live_ai_advice")  # preserve old advice

    with metrics_box:
        c1, c2, c3 = st.columns(3)
        c1.metric('Temperature (°C)', parsed['temp'])
        c2.metric('Humidity (%)', parsed['humidity'])
        c3.metric('Soil moisture (%)', parsed['soil_moisture'])

        st.markdown('---')
        st.success(f'🌿 Plant health prediction: {prediction}')

        recs = get_recommendation(parsed['temp'], parsed['humidity'], parsed['soil_moisture'], prediction)
        st.info('📋 Recommendations:')
        for r in recs:
            st.write(f'- {r}')

        st.caption(f'Last read: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {firebase_status}')

    status_box.success('✅ Sensor data processed successfully')


button_read = st.button('📡 Read Sensor (manual)')

if button_read or auto_refresh:
    process_sensor_reading()

# ── AI Plant Advisor ──────────────────────────────────────────────────────────
# Rendered OUTSIDE process_sensor_reading so it persists when AI button is clicked
if "live_prediction" in st.session_state:
    st.markdown("---")
    st.subheader("🤖 AI Plant Advisor (Groq)")

    if st.button("🔍 Ask AI for plant advice"):
        stats = get_plant_stats(PLANT_ID)
        with st.spinner("🌿 Consulting AI plant advisor..."):
            advice = get_plant_advice(
                st.session_state["live_temp"],
                st.session_state["live_humidity"],
                st.session_state["live_soil"],
                st.session_state["live_prediction"],
                stats
            )
        st.session_state["live_ai_advice"] = advice

    if st.session_state.get("live_ai_advice"):
        st.info(st.session_state["live_ai_advice"])
    else:
        st.caption("Click the button above to get an AI-powered analysis of your plant's condition.")

# ── Alert Dashboard ───────────────────────────────────────────────────────────
if "live_prediction" in st.session_state:
    st.markdown("---")
    st.subheader("🚨 Live Streamlit Alert Panel")
    
    if not st.session_state.alert_history:
        st.success("🟢 No abnormal conditions detected recently.")
    else:
        latest_alert = st.session_state.alert_history[0]
        color = "#ff4b4b" if latest_alert['priority'] == "CRITICAL" else "#ffa000"
        
        # Highlight latest alert
        st.markdown(
            f"""
            <div style="border: 2px solid {color}; padding: 10px; border-radius: 5px; background-color: {color}11;">
                <h4 style="margin:0; color: {color};">[{latest_alert['priority']}] {latest_alert['msg']}</h4>
                <small>Last triggered: {latest_alert['time']}</small>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        with st.expander("Show Alert History (Last 10)"):
            for alert in st.session_state.alert_history:
                icon = "🔴" if alert['priority'] == "CRITICAL" else "🟡"
                st.markdown(f"`{alert['time']}` | {icon} **{alert['priority']}** | {alert['msg']}")

# ── Firebase status, Alerts, Stats, Graphs ────────────────────────────────────
# Rendered OUTSIDE process_sensor_reading so alert Mark-Read button works correctly
if "live_prediction" in st.session_state:
    st.markdown("---")
    st.subheader("📊 Firebase Database Status")

    firebase_data = get_recent_sensor_data(PLANT_ID, limit=10)
    if firebase_data:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Firebase Records", len(firebase_data))
        with col2:
            latest = firebase_data[0]
            st.metric("Latest Prediction", latest.get('plant_health', 'N/A'))

        # Alerts — each alert dict includes 'id' from get_unread_alerts()
        alerts = get_unread_alerts(PLANT_ID)
        if alerts:
            st.error(f"🚨 {len(alerts)} unread alert(s)")
            for alert in alerts[:5]:
                alert_id  = alert.get('id', '')
                ts_raw    = alert.get('timestamp')
                # Firestore returns DatetimeWithNanoseconds — convert safely
                if hasattr(ts_raw, 'strftime'):
                    ts_label = ts_raw.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    ts_label = str(ts_raw)[:19]

                st.warning(f"**{alert.get('type', 'Alert')}**: {alert.get('message', '')}")
                if st.button(f"✅ Mark Read — {ts_label}", key=f"markread_{alert_id}"):
                    mark_alerts_read(PLANT_ID, [alert_id])
                    st.rerun()
        else:
            st.success("✅ No active alerts")
    else:
        st.warning("⚠️ No Firebase data available yet — read a sensor first")

    # 24h statistics
    stats = get_plant_stats(PLANT_ID)
    if stats and stats.get('total_readings', 0) > 0:
        st.markdown("### 📈 24h Statistics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Readings",  stats.get('total_readings', 0))
        col2.metric("Avg Temp (°C)",   f"{stats.get('avg_temperature', 0):.1f}")
        col3.metric("Avg Humidity (%)", f"{stats.get('avg_humidity', 0):.1f}")
        col4.metric("Avg Soil (%)",    f"{stats.get('avg_soil_moisture', 0):.1f}")

    # Real-time graphs (session data only — resets on page refresh)
    if not st.session_state.df.empty:
        st.markdown("### 📈 Real-Time Sensor Graphs")
        df = st.session_state.df.copy()
        df["time"] = pd.to_datetime(df["time"]).dt.strftime("%H:%M")
        df = df.set_index("time")
        st.subheader("🌡 Temperature vs Time")
        st.line_chart(df["temp"])
        st.subheader("💧 Humidity vs Time")
        st.line_chart(df["humidity"])
        st.subheader("🌱 Soil Moisture vs Time")
        st.line_chart(df["soil"])

if auto_refresh:
    if st_autorefresh is None:
        st.warning('Install streamlit-autorefresh: pip install streamlit-autorefresh for stable auto-update.')
    else:
        st_autorefresh(interval=interval * 1000, limit=None, key='live_refresh')

st.write('---')
st.markdown('**Notes:**')
st.write('- Ensure ESP32 is on the same WiFi network and the IP matches ESP_URL at the top of this file.')
st.write('- ESP32 should return JSON with keys: temp, humidity, soil')