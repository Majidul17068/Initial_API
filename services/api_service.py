import requests
import os
from dotenv import load_dotenv

load_dotenv()

def reset_user_transcript(conversation_id):
    url = f"{os.getenv('VOICE_TRANSCRIPT_API_ENDPOINT')}/reset-user-text/?conversation_id={conversation_id}"
    try:
        requests.get(url, timeout=5)
    except requests.RequestException as e:
        print(f"Error resetting transcript: {e}")

def fetch_user_transcript(conversation_id):
    url = f"{os.getenv('VOICE_TRANSCRIPT_API_ENDPOINT')}/get-user-text/?conversation_id={conversation_id}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        print(f"Error fetching transcript: {e}")
    return {"conversation_id": conversation_id, "text": ""}

def fetch_is_speaking(conversation_id):
    url = f"{os.getenv('VOICE_TRANSCRIPT_API_ENDPOINT')}/get-is-speaking/?conversation_id={conversation_id}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        print(f"Error checking speaking status: {e}")
    return {"conversation_id": conversation_id, "is_speaking": False}
