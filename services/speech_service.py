import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import PropertyId
import streamlit as st
from services.groq_service import GroqService
import os
from dotenv import load_dotenv
import re
import time
import threading
load_dotenv()
# Function to add custom CSS for chatbot layout
def add_custom_css():
   st.markdown(
       """
       <style>
       .user-message, .bot-message {
           display: flex;
           align-items: center;
           margin: 10px 0;
       }
       .bot-message {
           justify-content: flex-start;
       }
       .user-message {
           justify-content: flex-end;
       }
       .avatar {
           width: 40px;
           height: 40px;
           border-radius: 50%;
           margin: 0 10px;
       }
       .message-text {
           background-color: #f1f0f0;
           padding: 10px;
           color: #000;
           border-radius: 10px;
           max-width: 70%;
       }
       .user-message .message-text {
           background-color: #daf0da;
       }
       </style>
       """, unsafe_allow_html=True
   )


# Display chatbot messages
def display_chat_message(is_user, message_text):
   avatar_bot = "https://www.w3schools.com/howto/img_avatar.png"
   avatar_user = "https://www.w3schools.com/howto/img_avatar2.png"
  
   if is_user:
       st.markdown(f"""
       <div class="user-message">
           <div class="message-text">{message_text}</div>
           <img src="{avatar_user}" alt="User Avatar" class="avatar">
       </div>
       """, unsafe_allow_html=True)
   else:
       st.markdown(f"""
       <div class="bot-message">
           <img src="{avatar_bot}" alt="Bot Avatar" class="avatar">
           <div class="message-text">{message_text}</div>
       </div>
       """, unsafe_allow_html=True)
# Speech service class using Azure Speech SDK
class SpeechService:
   def __init__(self):
       self.speech_config = speechsdk.SpeechConfig(
           subscription=os.getenv("AZURE_SPEECH_KEY"),
           region=os.getenv("AZURE_SPEECH_REGION")
       )
       self.audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
       self.speech_config.speech_synthesis_voice_name = "en-GB-BellaNeural"
       self.speech_synthesizer = speechsdk.SpeechSynthesizer(
           speech_config=self.speech_config,
           audio_config=self.audio_config
       )
       self.speech_recognizer = speechsdk.SpeechRecognizer(
           speech_config=self.speech_config,
           audio_config=self.audio_config
       )
       self.groq_service = GroqService()
       self.recognized_text = ""
       # Event handlers for continuous recognition
       self.speech_recognizer.recognized.connect(self.recognized_handler)
       self.speech_recognizer.session_started.connect(lambda evt: st.info("Speech recognition started."))
       self.speech_recognizer.session_stopped.connect(lambda evt: st.info("Speech recognition stopped."))
       self.speech_recognizer.canceled.connect(self.canceled_handler)
   def set_dynamic_timeouts(self, segment_timeout: int , initial_timeout: int):
       """Sets the dynamic timeouts for the speech recognizer."""
       self.speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(segment_timeout))
       self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(initial_timeout))
   
   def recognized_handler(self, evt):
        """Handler to process recognized speech."""
        recognized_text = evt.result.text.strip().lower()
        if recognized_text:
            self.recognized_text = recognized_text

  
   def canceled_handler(self, evt):
       """Handler to process canceled recognition events."""
       st.error(f"Speech recognition canceled: {evt.result.reason}")
       self.stop_speech_recognition()

   def start_continuous_recognition(self):
       """Start continuous speech recognition."""
       try:
           self.recognized_text = "" 
           self.speech_recognizer.start_continuous_recognition()
           st.info("Speech recognition started.")
       except Exception as e:
           st.error(f"Error starting continuous recognition: {e}")
           
   def stop_speech_recognition(self):
        """Stop continuous speech recognition and return recognized text."""
        try:
            self.speech_recognizer.stop_continuous_recognition()
            st.info("Speech recognition stopped.")
            # Remove the display_chat_message call from here
            return self.recognized_text
        except Exception as e:
            st.error(f"Error stopping speech recognition: {e}")
            return None
   def synthesize_speech(self, text: str):
       cleaned_text = self.clean_text(text)
      
       # Display the entire text at once
       display_chat_message(is_user=False, message_text=cleaned_text)
      
       # Start speech synthesis in a separate thread
       synthesis_thread = threading.Thread(target=self._synthesize_speech_thread, args=(cleaned_text,))
       synthesis_thread.start()
      
       # Wait for speech synthesis to complete
       synthesis_thread.join()
      
       return True


   def _synthesize_speech_thread(self, text: str):
       result = self.speech_synthesizer.speak_text_async(text).get()
       if result.reason == speechsdk.ResultReason.Canceled:
           cancellation_details = result.cancellation_details
           st.error(f"Speech synthesis canceled: {cancellation_details.reason}")


   @staticmethod
   def clean_text(text: str):
       """Remove special characters from text."""
       return ''.join(char for char in text if re.match(r'[\w\s\.,!?\'":;()-]', char))


