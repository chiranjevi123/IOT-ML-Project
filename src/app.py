import streamlit as st
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
from firebase import get_recent_sensor_data, get_unread_alerts, get_plant_stats
from ai_advisor import get_plant_advice

# ── Resolve paths relative to this file so it works from any CWD ──────────────
BASE_DIR = Path(__file__).parent.parent  # project root


def get_recommendation(temp, humidity, soil, prediction):
    """Generate recommendation based on all sensor inputs"""
    recommendations = []

    if temp < 15:
        recommendations.append("🌡️ Temperature too low - move plant to warmer location")
    elif temp > 35:
        recommendations.append("🔥 Temperature too high - provide shade/cooling")

    if humidity < 30:
        recommendations.append("💨 Humidity too low - mist plant leaves")
    elif humidity > 80:
        recommendations.append("💧 Humidity too high - improve air circulation")

    if soil < 25:
        recommendations.append("💧 Water plant immediately")
    elif soil < 40:
        recommendations.append("⚠️ Check soil, may need watering soon")
    elif soil > 70:
        recommendations.append("⛔ Reduce watering - soil is too wet (risk of root rot)")

    if not recommendations:
        if prediction == "Healthy":
            recommendations.append("✅ Plant conditions are optimal - maintain current care")
        elif prediction == "Moderate":
            recommendations.append("⚠️ Monitor plant closely - minor adjustments may be needed")
        else:
            recommendations.append("🚨 Plant is stressed - check all conditions")

    return recommendations


# Load model and scaler
try:
    model = pickle.load(open(BASE_DIR / "model.pkl", "rb"))
    scaler = pickle.load(open(BASE_DIR / "scaler.pkl", "rb"))
except FileNotFoundError:
    st.error("❌ Error: model.pkl or scaler.pkl not found. Please run train_model.py first!")
    st.stop()

st.set_page_config(page_title="Smart Plant Monitor", layout="centered")
st.title("🌱 Smart Soil & Plant Health Monitoring")
st.write("Predict plant health using environmental conditions")
st.markdown("---")

# Input Section
st.subheader("📊 Enter Sensor Values")
temp = st.slider("🌡️ Temperature (°C)", 10.0, 50.0, 30.0)
humidity = st.slider("💧 Humidity (%)", 10.0, 100.0, 50.0)
soil = st.slider("🌱 Soil Moisture (%)", 0, 100, 50)

# ── Predict button — stores result in session_state ───────────────────────────
if st.button("🔍 Predict Plant Health"):
    features = np.array([[temp, humidity, soil]])
    features_scaled = scaler.transform(features)
    prediction = model.predict(features_scaled)[0]

    # Persist everything needed for subsequent reruns (e.g. AI button click)
    st.session_state["prediction"] = prediction
    st.session_state["last_temp"] = temp
    st.session_state["last_humidity"] = humidity
    st.session_state["last_soil"] = soil
    st.session_state["pred_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["ai_advice"] = None  # reset advice when new prediction is made

# ── Results section — rendered from session_state, visible across all reruns ──
if "prediction" in st.session_state:
    pred        = st.session_state["prediction"]
    last_temp   = st.session_state["last_temp"]
    last_hum    = st.session_state["last_humidity"]
    last_soil   = st.session_state["last_soil"]
    pred_ts     = st.session_state["pred_timestamp"]

    st.markdown("---")
    st.subheader("🌿 Prediction Result")
    st.caption(f"⏱️ Prediction made at: {pred_ts}")
    st.success(f"Plant Health: **{pred}**")

    recommendations = get_recommendation(last_temp, last_hum, last_soil, pred)
    st.info("📋 Recommendations:")
    for rec in recommendations:
        st.write(rec)

    # ── AI Plant Advisor ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🤖 AI Plant Advisor (Groq)")

    if st.button("🔍 Ask AI for plant advice"):
        stats = get_plant_stats("plant_001")
        with st.spinner("🌿 Consulting AI plant advisor..."):
            advice = get_plant_advice(last_temp, last_hum, last_soil, pred, stats)
        st.session_state["ai_advice"] = advice

    if st.session_state.get("ai_advice"):
        st.info(st.session_state["ai_advice"])
    else:
        st.caption("Click the button above to get an AI-powered analysis of your plant's condition.")

    # ── Firebase section ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Database & Alert Status")

    firebase_data = get_recent_sensor_data("plant_001", limit=5)
    if firebase_data:
        st.write("**Recent Sensor Readings from Database:**")
        for reading in firebase_data[:3]:
            ts = reading.get('timestamp', 'N/A')
            if hasattr(ts, 'strftime'):
                ts = ts.strftime('%H:%M:%S')
            st.write(
                f"🕐 {ts} | 🌡 {reading.get('temperature', 'N/A')}°C | "
                f"💧 {reading.get('humidity', 'N/A')}% | "
                f"🌱 {reading.get('soil_moisture', 'N/A')}% → {reading.get('plant_health', 'N/A')}"
            )
    else:
        st.warning("⚠️ No historical data in database")

    alerts = get_unread_alerts("plant_001")
    if alerts:
        st.error(f"🚨 {len(alerts)} Active Alert(s)")
        for alert in alerts[:2]:
            st.warning(f"**{alert.get('type', 'Alert')}**: {alert.get('message', '')}")
    else:
        st.success("✅ No active alerts")

    stats = get_plant_stats("plant_001")
    if stats and stats.get('total_readings', 0) > 0:
        st.markdown("### 📈 Plant Statistics (24h)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Readings", stats.get('total_readings', 0))
        col2.metric("Avg Temp", f"{stats.get('avg_temperature', 0):.1f}°C")
        col3.metric("Avg Soil", f"{stats.get('avg_soil_moisture', 0):.1f}%")
