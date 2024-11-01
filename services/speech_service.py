import azure.cognitiveservices.speech as speechsdk
import time
import os
import re
import threading
from services.ui_helpers import display_chat_message
import streamlit as st
from services.api_service import fetch_user_transcript , fetch_is_speaking

from load_azure_sdk import load_azure_speech_sdk, load_azure_synthetic_speech_sdk

class SpeechService:
    def __init__(self, conversation_manager, conversation_id):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION")
        )

        self.audio_config_recognizer = None
        #speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.audio_config_synthesizer = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        self.speech_config.speech_synthesis_voice_name = "en-GB-BellaNeural"
        self.speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=self.audio_config_recognizer
        )
        # self.speech_synthesizer = speechsdk.SpeechSynthesizer(
        #     speech_config=self.speech_config,
        #     audio_config=self.audio_config_synthesizer
        # )
        
        self.recognized_text = []
        self.status_message = ""
        
        self.is_recognizing = False
        
        self.lock = threading.Lock()
        self.last_recognition_time = time.time()
        self.is_recognizing = False  
        self.conversation_manager = conversation_manager
        self.conversation_id = conversation_id

        # self.speech_recognizer.recognizing.connect(self.recognizing_callback)
        # self.speech_recognizer.recognized.connect(self.recognized_callback)
        self.speech_recognizer.session_started.connect(self.session_started_handler)
        self.speech_recognizer.session_stopped.connect(self.session_stopped_handler)
        self.speech_recognizer.canceled.connect(self.canceled_handler)

    def recognizing_callback(self, evt):
        self.last_recognition_time = time.time()

    def recognized_callback(self, text):
        if text != "":
            with self.lock:
                self.recognized_text.append(text)
             
        # if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
        #     with self.lock:
        #         self.recognized_text.append(evt.result.text)
        #     self.last_recognition_time = time.time()
        # elif evt.result.reason == speechsdk.ResultReason.NoMatch:
        #     print("No speech recognized.")

    def session_started_handler(self):
        with self.lock:
            self.status_message = "Speech recognition started."
            self.is_recognizing = True 

    def session_stopped_handler(self):
        with self.lock:
            self.status_message = "Speech recognition stopped."
            self.is_recognizing = False  

    def canceled_handler(self, evt):
        with self.lock:
            self.status_message = f"Speech recognition canceled: {evt.result.reason}"
        print(self.status_message)

    def start_continuous_recognition(self, duration=20, silence_threshold=1.0):
        if self.is_recognizing:
            return ""

        self.conversation_manager.display_status('info', "Speech recognition started. Please speak now.")
        with self.lock:
            self.recognized_text = []
            self.status_message = ""
        
        self.last_recognition_time = time.time()
        self.session_started_handler()
        
        load_azure_speech_sdk(self.conversation_id)
        
        # Start continuous recognition in a new thread
        # recognition_thread = threading.Thread(target=self._continuous_recognition_loop, args=(duration, silence_threshold))
        # recognition_thread.start()
        return self._continuous_recognition_loop()

    def _continuous_recognition_loop(self):
        self.is_recognizing = True
        full_text = ""
        
        while self.is_recognizing and (full_text == "" or full_text is not None):
            time.sleep(2)  # Call the function every second
            ut = fetch_user_transcript(self.conversation_id)
            print('api call: ', ut)
            full_text = ut['text']
            if full_text != "":
                self.recognized_callback(full_text)
                self.stop_speech_recognition()
                break
            
        return full_text
        
        
        # return full_text

    def stop_speech_recognition(self):
        if not self.is_recognizing:
            print("Recognition is not currently active.")
            return

        try:
            # self.speech_recognizer.stop_continuous_recognition()
            self.session_stopped_handler()
            self.conversation_manager.display_status('info',"Speech recognition stopped")
        except Exception as e:
            with self.lock:
                self.status_message = f"Error stopping speech recognition: {e}"
            print(self.status_message)

    def synthesize_speech(self, text: str):
        cleaned_text = self.clean_text(text)
        display_chat_message(is_user=False, message_text=cleaned_text)
        
        # synthesis_complete = threading.Event()
        
        # synthesis_thread = threading.Thread(
        #     target=self._synthesize_speech_thread, 
        #     args=(cleaned_text, synthesis_complete)
        # )
        # synthesis_thread.start()
        load_azure_synthetic_speech_sdk(text, self.conversation_id)
        # while not synthesis_complete.is_set():
        #     time.sleep(0.1)
        
        is_speaking = True
        
        while is_speaking:
            time.sleep(2)  # Call the function every second
            ut = fetch_is_speaking(self.conversation_id)
            print('api call: ', ut)
            is_speaking = ut['is_speaking']
            if not is_speaking:
                break
            
        return True

    @staticmethod
    def clean_text(text: str):
        return ''.join(char for char in text if re.match(r'[\w\s\.!?\'":;()<>\-]', char))
