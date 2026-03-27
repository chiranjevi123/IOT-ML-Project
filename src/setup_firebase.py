#!/usr/bin/env python3
"""
Firebase Setup Script for IoT Plant Monitoring System

This script helps you set up Firebase for your project.
"""

def create_firebase_instructions():
    """Create setup instructions for Firebase"""

    instructions = """
# 🔥 Firebase Setup Instructions

## 1. Create Firebase Project
1. Go to https://console.firebase.google.com/
2. Click "Create a project" or "Add project"
3. Enter project name: `iot-plant-monitor`
4. Enable Google Analytics (optional)
5. Choose account and create project

## 2. Enable Required Services

### Firestore Database
1. Go to "Firestore Database" in the left menu
2. Click "Create database"
3. Choose "Start in test mode" (for development)
4. Select a location (choose closest to you)

### Firebase Cloud Messaging (for notifications)
1. Go to "Cloud Messaging" in the left menu
2. This should be enabled by default

## 3. Generate Service Account Key
1. Go to Project Settings (gear icon)
2. Go to "Service accounts" tab
3. Click "Generate new private key"
4. Download the JSON file
5. **IMPORTANT**: Rename it to `firebase-credentials.json`
6. Place it in your project root directory

## 4. Environment Setup
Set the environment variable (optional, script will look for firebase-credentials.json by default):

```bash
# Windows
set FIREBASE_CREDENTIALS=firebase-credentials.json

# Linux/Mac
export FIREBASE_CREDENTIALS=firebase-credentials.json
```

## 5. Test Firebase Connection
Run this script to test your Firebase setup:

```bash
python setup_firebase.py
```

## 6. Firebase Security Rules (Optional)
For production, update Firestore rules in Firebase Console:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read/write for development
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

## 7. Mobile App Setup (Optional)
If you want push notifications on mobile:

1. Add Firebase to your mobile app
2. Subscribe to topic: `plant_plant_001_alerts`
3. Handle incoming notifications

---
**Note**: Keep your service account key secure and never commit it to version control!
"""

    with open('FIREBASE_SETUP.md', 'w') as f:
        f.write(instructions)

    print("✅ Firebase setup instructions created: FIREBASE_SETUP.md")

def test_firebase_connection():
    """Test Firebase connection"""
    try:
        from firebase import initialize_firebase, save_sensor_data, get_recent_sensor_data

        if initialize_firebase():
            print("✅ Firebase initialized successfully")

            # Test save
            test_id = save_sensor_data("plant_001", 25.0, 60.0, 50.0, "Healthy")
            if test_id:
                print(f"✅ Test data saved successfully (ID: {test_id[:8]}...)")

                # Test retrieve
                data = get_recent_sensor_data("plant_001", limit=1)
                if data:
                    print("✅ Data retrieval successful")
                    print(f"   Latest reading: {data[0]}")
                else:
                    print("⚠️ Data retrieval returned empty")
            else:
                print("❌ Failed to save test data")

        else:
            print("❌ Firebase initialization failed")
            print("   Check your credentials file and internet connection")

    except ImportError:
        print("❌ Firebase dependencies not installed")
        print("   Run: pip install firebase-admin")
    except Exception as e:
        print(f"❌ Firebase test failed: {e}")

if __name__ == "__main__":
    print("🔥 Firebase Setup for IoT Plant Monitoring")
    print("=" * 50)

    create_firebase_instructions()

    print("\n🧪 Testing Firebase connection...")
    test_firebase_connection()

    print("\n📖 Next steps:")
    print("1. Follow FIREBASE_SETUP.md instructions")
    print("2. Place firebase-credentials.json in project root")
    print("3. Run your apps: python data_logger.py, streamlit run app.py")
    print("\n🎉 Firebase setup complete!")