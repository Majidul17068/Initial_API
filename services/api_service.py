import requests
import os
from dotenv import load_dotenv
load_dotenv()

def reset_user_transcript(conversation_id):
    """
    Makes an API call to fetch conversations based on resident_id, resident_name, and event_type.
    """
    url = f"{os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT")}/reset-user-text/?conversation_id={conversation_id}"
    headers = {
        "Content-Type": "application/json"
    }
    requests.get(url, headers=headers)



def fetch_user_transcript(conversation_id):
    """
    Makes an API call to fetch conversations based on resident_id, resident_name, and event_type.
    """
    url = f"{os.getenv("VOICE_TRANSCRIPT_API_ENDPOINT")}/get-user-text/?conversation_id={conversation_id}"
    headers = {
        "Content-Type": "application/json"
    }


    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"conversation_id": conversation_id, "text": ""}

def fetch_is_speaking(conversation_id):
    """
    Makes an API call to check if a conversation is marked as speaking based on the conversation_id.
    """
    # Construct the URL for the `get-is-speaking` endpoint
    url = f"{os.getenv('VOICE_TRANSCRIPT_API_ENDPOINT')}/get-is-speaking/?conversation_id={conversation_id}"
    headers = {
        "Content-Type": "application/json"
    }


    try:
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Received status code {response.status_code}")
            return {"conversation_id": conversation_id, "is_speaking": False}
    
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return {"conversation_id": conversation_id, "is_speaking": False}