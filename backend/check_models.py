import os
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print("Available Models:")
        found = False
        target = "gemini-2.5-flash-native-audio-preview-12-2025"
        for m in models:
            print(f"- {m['name']}")
            if target in m['name']:
                found = True
        
        if found:
            print(f"\nSUCCESS: Model '{target}' found!")
        else:
            print(f"\nWARNING: Model '{target}' NOT found in list.")
    else:
        print(f"Error listing models: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Connection Error: {e}")