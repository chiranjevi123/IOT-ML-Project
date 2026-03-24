import streamlit as st
import serial
import pickle
from datetime import datetime
import requests   
import pandas as pd 
from firebase import (get_recent_sensor_data, get_unread_alerts, mark_alerts_read,
                      get_plant_stats, save_sensor_data, send_plant_alert)
# for auto-refresh without unsupported API
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# ----------- Configuration -----------
DEFAULT_PORT = 'COM8'
DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 1

# ✅ ADD YOUR ESP32 IP HERE
ESP_URL = "http://192.168.157.94/data"   # 🔴 CHANGE THIS

# Firebase Plant ID
PLANT_ID = "plant_001"

@st.cache_resource
def get_serial_connection(port, baudrate, timeout=1):
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        return ser
    except serial.SerialException as e:
        st.error(f"⚠️ Serial port error: {e}")
        return None
    except Exception as e:
        st.error(f"⚠️ Unexpected serial error: {e}")
        return None

# ----------- UPDATED PARSER (NO CHANGE) -----------
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

    if len(fields) != 4 or raw.count(',') != 3:
        return None, f"Incomplete/invalid data: {fields}"

    try:
        temp = float(fields[0])
        humidity = float(fields[1])
        soil_raw = float(fields[2])
        soil_moisture = float(fields[3])        
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

# ----------- REST CODE SAME -----------

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

    if not recs:
        recs.append("✅ All parameters are in nominal range.")
    return recs

st.set_page_config(page_title='Live IoT Plant Monitor', layout='wide', initial_sidebar_state='expanded')

st.title('🌱 IoT Live Plant Monitoring (ESP32)')
st.write('Use this dashboard with your ESP32 sensor stream. Adjust port and click `Read Sensor`.')

with st.sidebar:
    st.header('Serial Settings')
    port = st.text_input('Serial port', DEFAULT_PORT)
    baud = st.number_input('Baud rate', value=DEFAULT_BAUD, step=4800)
    auto_refresh = st.checkbox('Auto-refresh (until stopped)', value=False)
    interval = st.slider('Refresh interval (seconds)', 1, 10, value=2)

try:
    model = pickle.load(open('model.pkl', 'rb'))
    scaler = pickle.load(open('scaler.pkl', 'rb'))
except FileNotFoundError:
    st.error('❌ model.pkl or scaler.pkl not found. Run train_model.py first, then restart this app.')
    st.stop()

ser = get_serial_connection(port=port, baudrate=baud, timeout=DEFAULT_TIMEOUT)

status_box = st.empty()
metrics_box = st.container()
log_box = st.expander('Raw log & debug output', expanded=False)

# ✅ ----------- GRAPH STORAGE -----------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["time", "temp", "humidity", "soil"])

def process_sensor_reading():
    try:
        response = requests.get(ESP_URL, timeout=2)
        data = response.json()

        line = f"{data['temp']},{data['humidity']},{data['soil']*30},{data['soil']}".strip()

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

    # ✅ STORE DATA
    new_row = {
        "time": datetime.now(),
        "temp": parsed['temp'],
        "humidity": parsed['humidity'],
        "soil": parsed['soil_moisture']
    }

    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])])
    st.session_state.df = st.session_state.df.tail(200)   # ✅ UPDATED (long-term patterns)

    x = [[parsed['temp'], parsed['humidity'], parsed['soil_moisture']]]
    x_scaled = scaler.transform(x)
    prediction = model.predict(x_scaled)[0]

    # 🔥 SAVE EVERY READING TO FIREBASE (for trends & future predictions)
    doc_id = save_sensor_data(PLANT_ID, parsed['temp'], parsed['humidity'],
                              parsed['soil_moisture'], prediction)
    if doc_id:
        firebase_status = f"✅ Saved to Firebase (ID: {doc_id[:8]}...)"
    else:
        firebase_status = "⚠️ Firebase save failed"

    # 🚨 SEND ALERT FOR UNHEALTHY CONDITIONS
    if prediction == "Unhealthy":
        sensor_info = {
            'temperature': parsed['temp'],
            'humidity': parsed['humidity'],
            'soil_moisture': parsed['soil_moisture']
        }
        send_plant_alert(PLANT_ID, "Unhealthy", sensor_info)

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

        # 🔥 ----------- FIREBASE DATA & ALERTS -----------
        st.markdown("---")
        st.subheader("📊 Firebase Database Status")

        # Show recent Firebase data
        firebase_data = get_recent_sensor_data("plant_001", limit=10)
        if firebase_data:
            firebase_df = pd.DataFrame(firebase_data)
            firebase_df['timestamp'] = pd.to_datetime(firebase_df['timestamp']).dt.strftime('%H:%M:%S')

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Firebase Records", len(firebase_data))
            with col2:
                if len(firebase_data) > 0:
                    latest = firebase_data[0]
                    st.metric("Latest Prediction", latest.get('plant_health', 'N/A'))

            # Show alerts
            alerts = get_unread_alerts("plant_001")
            if alerts:
                st.error(f"🚨 {len(alerts)} unread alert(s)")
                for alert in alerts[:3]:  # Show last 3 alerts
                    st.warning(f"{alert.get('type', 'Alert')}: {alert.get('message', '')}")
                    if st.button(f"Mark Read - {alert.get('timestamp', '')[:19]}", key=f"alert_{alert.get('timestamp', '')}"):
                        mark_alerts_read("plant_001", [alert.get('id', '')])
                        st.rerun()
            else:
                st.success("✅ No active alerts")
        else:
            st.warning("⚠️ No Firebase data available")

        # Show plant statistics
        stats = get_plant_stats("plant_001")
        if stats:
            st.markdown("### 📈 24h Statistics")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Readings", stats.get('total_readings', 0))
            col2.metric("Avg Temp (°C)", f"{stats.get('avg_temperature', 0):.1f}")
            col3.metric("Avg Humidity (%)", f"{stats.get('avg_humidity', 0):.1f}")
            col4.metric("Avg Soil (%)", f"{stats.get('avg_soil_moisture', 0):.1f}")

        # ✅ ----------- GRAPHS WITH TIME FORMAT -----------

        st.markdown("### 📈 Real-Time Sensor Graphs")

        df = st.session_state.df.copy()
        df["time"] = pd.to_datetime(df["time"]).dt.strftime("%H:%M")  # ✅ HH:mm format
        df = df.set_index("time")

        st.subheader("🌡 Temperature vs Time")
        st.line_chart(df["temp"])

        st.subheader("💧 Humidity vs Time")
        st.line_chart(df["humidity"])

        st.subheader("🌱 Soil Moisture vs Time")
        st.line_chart(df["soil"])

    status_box.success('✅ Sensor data processed successfully')

button_read = st.button('📡 Read Sensor (manual)')

if button_read or auto_refresh:
    process_sensor_reading()

if auto_refresh:
    if st_autorefresh is None:
        st.warning('Install streamlit-autorefresh: pip install streamlit-autorefresh for stable auto-update.')
    else:
        st_autorefresh(interval=interval * 1000, limit=None, key='live_refresh')

st.write('---')
st.markdown('**Notes:**')
st.write('- For stable operation, avoid continuous while loops in Streamlit. Use manual refresh or auto-refresh with controlled interval.')
st.write('- Ensure ESP32 is writing data in `temp,humidity,soil_moisture` format.')