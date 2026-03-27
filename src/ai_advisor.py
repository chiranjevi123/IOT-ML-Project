"""
AI Plant Advisor — uses Groq API to give a natural-language summary
of the plant's current condition based on sensor data and ML prediction.
"""

import os
from dotenv import load_dotenv

# Load .env from project root (works regardless of where the script is run from)
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")


def get_plant_advice(temp: float, humidity: float, soil: float,
                     prediction: str, stats: dict = None) -> str:
    """
    Call Groq LLM with current sensor readings and ML prediction.

    Args:
        temp:       Current temperature in °C
        humidity:   Current humidity in %
        soil:       Current soil moisture in %
        prediction: ML model output — "Healthy", "Moderate", or "Unhealthy"
        stats:      Optional dict with 24h averages from Firebase
                    (keys: avg_temperature, avg_humidity, avg_soil_moisture, total_readings)

    Returns:
        AI-generated advice string, or an error message string.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "❌ GROQ_API_KEY not found. Please add it to your .env file."

    try:
        from groq import Groq
    except ImportError:
        return "❌ groq package not installed. Run: pip install groq"

    # Build the prompt
    prompt_lines = [
        "You are a helpful plant care expert AI assistant.",
        "",
        "An IoT system is monitoring a plant and has collected the following data:",
        "",
        "Current sensor readings:",
        f"  - Temperature: {temp}°C",
        f"  - Humidity: {humidity}%",
        f"  - Soil Moisture: {soil}%",
        f"  - ML Model Health Prediction: {prediction}",
    ]

    if stats and stats.get('total_readings', 0) > 0:
        prompt_lines += [
            "",
            f"24-hour averages (based on {stats['total_readings']} readings):",
            f"  - Avg Temperature: {stats.get('avg_temperature', 0):.1f}°C",
            f"  - Avg Humidity: {stats.get('avg_humidity', 0):.1f}%",
            f"  - Avg Soil Moisture: {stats.get('avg_soil_moisture', 0):.1f}%",
        ]

    prompt_lines += [
        "",
        "Please provide:",
        "1. A 2-3 sentence summary of the plant's current condition.",
        "2. Two or three specific, actionable care steps the owner should take right now.",
        "",
        "Keep the response concise, practical, and easy to understand for a non-expert.",
        "Do not use markdown headers — plain text only.",
    ]

    prompt = "\n".join(prompt_lines)

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="openai/gpt-oss-20b",
            temperature=0.7,
            max_tokens=300,
        )
        return chat_completion.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ AI advisor error: {e}"
