
import streamlit as st
import pickle
import numpy as np
from datetime import datetime
from firebase import get_recent_sensor_data, get_unread_alerts, get_plant_stats

# Load model and scaler
try:
    model = pickle.load(open("model.pkl", "rb"))
    scaler = pickle.load(open("scaler.pkl", "rb"))
except FileNotFoundError:
    st.error("❌ Error: model.pkl or scaler.pkl not found. Please run train_model.py first!")
    st.stop()

st.set_page_config(page_title="Smart Plant Monitor", layout="centered")

# Title
st.title("🌱 Smart Soil & Plant Health Monitoring")
st.write("Predict plant health using environmental conditions")

st.markdown("---")

# Input Section
st.subheader("📊 Enter Sensor Values")
# The ML model uses 3 sensor features for predictions

temp = st.slider("🌡️ Temperature (°C)", 10.0, 50.0, 30.0)
humidity = st.slider("💧 Humidity (%)", 10.0, 100.0, 50.0)
soil = st.slider("🌱 Soil Moisture (%)", 0, 100, 50)

# Predict Button
if st.button("🔍 Predict Plant Health"):

    features = np.array([[temp, humidity, soil]])
    
    # IMPORTANT: Scale features before prediction (model was trained on scaled data)
    features_scaled = scaler.transform(features)

    prediction = model.predict(features_scaled)[0]

    # Smart Recommendation Logic (considers all factors)
    def get_recommendation(temp, humidity, soil, prediction):
        """Generate recommendation based on all sensor inputs"""
        recommendations = []
        
        # Temperature checks
        if temp < 15:
            recommendations.append("🌡️ Temperature too low - move plant to warmer location")
        elif temp > 35:
            recommendations.append("🔥 Temperature too high - provide shade/cooling")
        
        # Humidity checks
        if humidity < 30:
            recommendations.append("💨 Humidity too low - mist plant leaves")
        elif humidity > 80:
            recommendations.append("💧 Humidity too high - improve air circulation")
        
        # Soil moisture specific recommendations
        if soil < 25:
            recommendations.append("💧 Water plant immediately")
        elif soil < 40:
            recommendations.append("⚠️ Check soil, may need watering soon")
        elif soil > 70:
            recommendations.append("⛔ Reduce watering - soil is too wet (risk of root rot)")
        
        # If no specific issues, give general advice
        if not recommendations:
            if prediction == "Healthy":
                recommendations.append("✅ Plant conditions are optimal - maintain current care")
            elif prediction == "Moderate":
                recommendations.append("⚠️ Monitor plant closely - minor adjustments may be needed")
            else:
                recommendations.append("🚨 Plant is stressed - check all conditions")
        
        return recommendations
    
    recommendations = get_recommendation(temp, humidity, soil, prediction)

    # Display Results
    st.markdown("---")
    st.subheader("🌿 Prediction Result")
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"⏱️ Prediction made at: {timestamp}")

    st.success(f"Plant Health: {prediction}")

    st.info(f"📋 Recommendations:")
    for rec in recommendations:
        st.write(rec)

    # 🔥 ----------- FIREBASE INTEGRATION -----------
    st.markdown("---")
    st.subheader("📊 Database & Alert Status")

    # Show recent Firebase data
    firebase_data = get_recent_sensor_data("plant_001", limit=5)
    if firebase_data:
        st.write("**Recent Sensor Readings from Database:**")
        for reading in firebase_data[:3]:  # Show last 3 readings
            timestamp = reading.get('timestamp', 'N/A')
            if hasattr(timestamp, 'strftime'):
                timestamp = timestamp.strftime('%H:%M:%S')
            st.write(f"🕐 {timestamp} | 🌡 {reading.get('temperature', 'N/A')}°C | 💧 {reading.get('humidity', 'N/A')}% | 🌱 {reading.get('soil_moisture', 'N/A')}% → {reading.get('plant_health', 'N/A')}")
    else:
        st.warning("⚠️ No historical data in database")

    # Show alerts
    alerts = get_unread_alerts("plant_001")
    if alerts:
        st.error(f"🚨 {len(alerts)} Active Alert(s)")
        for alert in alerts[:2]:  # Show last 2 alerts
            st.warning(f"**{alert.get('type', 'Alert')}**: {alert.get('message', '')}")
    else:
        st.success("✅ No active alerts")

    # Show statistics
    stats = get_plant_stats("plant_001")
    if stats and stats.get('total_readings', 0) > 0:
        st.markdown("### 📈 Plant Statistics (24h)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Readings", stats.get('total_readings', 0))
        col2.metric("Avg Temp", f"{stats.get('avg_temperature', 0):.1f}°C")
        col3.metric("Avg Soil", f"{stats.get('avg_soil_moisture', 0):.1f}%")
