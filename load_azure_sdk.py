import os
from dotenv import load_dotenv
from services.api_service import reset_user_transcript

load_dotenv()

def load_azure_speech_sdk(conversation_id="-"):
    reset_user_transcript(conversation_id)

    js_func = f"""
    () => {{
        const subscriptionKey = '{os.getenv("AZURE_SPEECH_KEY")}';
        const serviceRegion = '{os.getenv("AZURE_SPEECH_REGION")}';
        const SpeechSDK = window.SpeechSDK;

        const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(subscriptionKey, serviceRegion);
        speechConfig.speechRecognitionLanguage = "en-US";
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        const speechRecognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

        speechRecognizer.startContinuousRecognitionAsync();
    }};
    """
    # Logic to render the component goes here (remove Streamlit-specific parts).
    return js_func
