# 🌱 IoT Smart Plant Health Monitoring System

An intelligent IoT-based system that monitors plant health using environmental sensors and machine learning predictions. This project combines ESP32 microcontroller sensors, real-time data collection, ML model training, and interactive web dashboards to provide automated plant care recommendations.

![Plant Health Monitoring](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![ESP32](https://img.shields.io/badge/ESP32-Arduino-orange) ![Streamlit](https://img.shields.io/badge/Streamlit-Web--App-red)

## 📋 Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Hardware Setup](#hardware-setup)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Collection](#data-collection)
- [Model Training](#model-training)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### 🌿 Smart Plant Health Classification
- **Real-time monitoring** of temperature, humidity, and soil moisture
- **ML-powered predictions** using Decision Tree and Random Forest models
- **Three health categories**: Healthy, Moderate, Unhealthy

### 🤖 Intelligent Recommendations
- **Contextual advice** based on sensor readings
- **Temperature management** (heating/cooling suggestions)
- **Humidity control** (misting/ventilation guidance)
- **Watering recommendations** (prevents over/under-watering)
- **Risk assessment** (root rot prevention, stress indicators)

### 📊 Interactive Dashboards
- **Manual prediction app** (`app.py`) - Input sliders for instant predictions
- **Live monitoring app** (`live_app.py`) - Real-time sensor data via serial/WiFi
- **Auto-refresh capability** for continuous monitoring
- **Data visualization** with pandas DataFrames

### 🔧 Data Management
- **Firebase Firestore** database for cloud storage
- **Real-time data synchronization** across devices
- **Automated data labeling** based on environmental thresholds
- **Push notifications** for critical plant conditions
- **Historical data retrieval** for model retraining
- **Noise filtering** and data validation

## 🛠 Technologies Used

### Hardware
- **ESP32 Microcontroller** - WiFi-enabled IoT device
- **DHT11/DHT22 Sensor** - Temperature and humidity measurement
- **Analog Soil Moisture Sensor** - Soil moisture detection

### Software
- **Python 3.8+** - Core programming language
- **Streamlit** - Web application framework
- **Firebase Admin SDK** - Cloud database and messaging
- **Scikit-learn** - Machine learning algorithms
- **Pandas & NumPy** - Data processing and analysis
- **Requests** - HTTP communication
- **PySerial** - Serial port communication
- **Arduino IDE** - ESP32 programming

### Machine Learning
- **Decision Tree Classifier** - Interpretable predictions
- **Random Forest Classifier** - Ensemble learning for accuracy
- **StandardScaler** - Feature normalization

## 💻 Hardware Requirements

- ESP32 development board
- DHT11 or DHT22 temperature/humidity sensor
- Analog soil moisture sensor
- Jumper wires and breadboard
- USB cable for programming
- Power supply (5V recommended)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/iot-plant-monitor.git
cd iot-plant-monitor
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Firebase Setup (Required)
```bash
# Run Firebase setup script
python setup_firebase.py

# Follow the instructions in FIREBASE_SETUP.md
# Download service account key and place as firebase-credentials.json
```

### 4. Install Arduino IDE
- Download and install [Arduino IDE](https://www.arduino.cc/en/software)
- Install ESP32 board support:
  - Go to **File > Preferences**
  - Add board manager URL: `https://dl.espressif.com/dl/package_esp32_index.json`
  - **Tools > Board > Boards Manager** - Install "esp32" by Espressif

### Dependencies (requirements.txt)
```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
requests>=2.31.0
pyserial>=3.5
streamlit-autorefresh>=0.1.0
attrs>=23.1.0
firebase-admin>=6.0.0
```

## 🔌 Hardware Setup

### ESP32 Sensor Connections

| ESP32 Pin | Sensor Pin | Description |
|-----------|------------|-------------|
| 3.3V | VCC | Power supply |
| GND | GND | Ground |
| GPIO 4 | DHT Data | Temperature/Humidity |
| GPIO 34 | Soil AOUT | Analog soil moisture |

### ESP32 Code Upload
1. Open `esp32_code.ino` in Arduino IDE
2. Select **Tools > Board > ESP32 Dev Module**
3. Set **Tools > Port** to your ESP32 COM port
4. Click **Upload** button
5. Monitor serial output for sensor data

## 📖 Usage

### 1. Train the ML Model
```bash
python train_model.py
```
This creates `model.pkl` and `scaler.pkl` files.

### 2. Manual Prediction Dashboard
```bash
streamlit run app.py
```
- Open browser to `http://localhost:8501`
- Adjust sliders for temperature, humidity, soil moisture
- Click "Predict Plant Health" for instant analysis

### 3. Live Monitoring Dashboard
```bash
streamlit run live_app.py
```
- Choose connection method (Serial or WiFi)
- Configure ESP32 IP address if using WiFi
- View real-time sensor data and predictions

### 4. Data Collection (Firebase)
```bash
python data_logger.py
```
- Collects sensor data via WiFi
- **Automatically saves to Firebase** instead of CSV
- **Sends push notifications** for unhealthy conditions
- Runs continuously until manually stopped (Ctrl+C)

### 5. Check Data Distribution
```bash
python check_distribution.py
```
- Analyzes class balance in training data

## 📁 Project Structure

```
iot_ml_project/
│
├── app.py                 # Manual prediction dashboard (with Firebase)
├── live_app.py           # Real-time monitoring dashboard (with Firebase)
├── train_model.py        # ML model training (loads from Firebase)
├── data_logger.py        # WiFi data collection (saves to Firebase)
├── firebase.py           # Firebase database & messaging functions
├── setup_firebase.py     # Firebase setup and testing script
├── check_distribution.py # Data analysis utility
│
├── esp32_code.ino       # ESP32 Arduino firmware
│
├── soil_data.csv        # Legacy CSV data
├── soil_dataa.csv       # Training dataset
├── model.pkl           # Trained ML model
├── scaler.pkl          # Feature scaler
├── firebase-credentials.json  # Firebase service account (create yourself)
│
├── requirements.txt     # Python dependencies
├── README.md           # Project documentation
├── FIREBASE_SETUP.md   # Firebase setup instructions
│
└── __pycache__/        # Python cache files
```

## 📊 Data Collection

The system uses intelligent labeling logic:

- **Unhealthy**: Soil < 30%, Temp > 38°C or < 10°C
- **Moderate**: Soil 30-60%, Humidity < 40%
- **Healthy**: All conditions optimal

Data includes timestamps and filtered sensor readings.

## 🧠 Model Training

### Features
- Temperature (°C)
- Humidity (%)
- Soil Moisture (%)

### Models Compared
- **Decision Tree** (max_depth=5)
- **Random Forest** (n_estimators=100, max_depth=7)

### Performance
- 80/20 train-test split with stratification
- Feature scaling with StandardScaler
- Best model selected based on accuracy

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings to functions
- Test hardware connections before committing
- Update README for new features

## 🙏 Acknowledgments

- ESP32 community for hardware support
- Streamlit for the amazing web app framework
- Scikit-learn for machine learning tools

## 📞 Support

If you encounter issues:
1. Check hardware connections
2. Verify Python environment and dependencies
3. Ensure ESP32 is programmed correctly
4. Check serial port settings

---

**Happy Gardening! 🌱** - Monitor your plants intelligently with IoT and ML.
