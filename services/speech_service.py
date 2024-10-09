import azure.cognitiveservices.speech as speechsdk
import time
import os
import re
import threading
from services.ui_helpers import display_chat_message
import streamlit as st

class SpeechService:
    def __init__(self, conversation_manager):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION")
        )
        self.audio_config_recognizer = speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.audio_config_synthesizer = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        self.speech_config.speech_synthesis_voice_name = "en-GB-BellaNeural"
        
        self.speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=self.audio_config_recognizer
        )
        self.speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=self.audio_config_synthesizer
        )
        
        self.recognized_text = []
        self.status_message = ""
        self.lock = threading.Lock()
        self.last_recognition_time = time.time()

        # Event handlers for continuous recognition
        self.speech_recognizer.recognizing.connect(self.recognizing_callback)
        self.speech_recognizer.recognized.connect(self.recognized_callback)
        self.speech_recognizer.session_started.connect(self.session_started_handler)
        self.speech_recognizer.session_stopped.connect(self.session_stopped_handler)
        self.speech_recognizer.canceled.connect(self.canceled_handler)
        
        self.conversation_manager = conversation_manager

    def recognizing_callback(self, evt):
        self.last_recognition_time = time.time()

    def recognized_callback(self, evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            with self.lock:
                self.recognized_text.append(evt.result.text)
            self.last_recognition_time = time.time()
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech recognized.")

    def session_started_handler(self, evt):
        with self.lock:
            self.status_message = "Speech recognition started."

    def session_stopped_handler(self, evt):
        with self.lock:
            self.status_message = "Speech recognition stopped."

    def canceled_handler(self, evt):
        with self.lock:
            self.status_message = f"Speech recognition canceled: {evt.result.reason}"
        print(self.status_message)

    def start_continuous_recognition(self, duration=120, silence_threshold=0.2):
        
        self.conversation_manager.display_status('info',"Speech recognition started. Please speak now.")
        # st.info("Speech recognition started. Please speak now.")
        with self.lock:
            self.recognized_text = []
            self.status_message = ""
        
        self.last_recognition_time = time.time()
        self.speech_recognizer.start_continuous_recognition()

        start_time = time.time()
        while time.time() - start_time < duration:
            time.sleep(0.1)
            if self.recognized_text and time.time() - self.last_recognition_time > silence_threshold:
                print(f"Silence detected for {silence_threshold} seconds. Stopping recognition.")
                break

        self.stop_speech_recognition()
        
        full_text = ' '.join(self.recognized_text)
        print(full_text)
        return full_text

    def stop_speech_recognition(self):
        try:
            self.speech_recognizer.stop_continuous_recognition()
            
            self.conversation_manager.display_status('info',"Speech recognition stopped.")
            # st.info("Speech recognition stopped.")
        except Exception as e:
            with self.lock:
                self.status_message = f"Error stopping speech recognition: {e}"
            print(self.status_message)

    def synthesize_speech(self, text: str):
        cleaned_text = self.clean_text(text)
        display_chat_message(is_user=False, message_text=cleaned_text)
        
        synthesis_complete = threading.Event()
        
        synthesis_thread = threading.Thread(
            target=self._synthesize_speech_thread, 
            args=(cleaned_text, synthesis_complete)
        )
        synthesis_thread.start()
        
        while not synthesis_complete.is_set():
            time.sleep(0.1)
        
        return True

    def _synthesize_speech_thread(self, text: str, synthesis_complete):
        try:
            result = self.speech_synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                with self.lock:
                    self.status_message = f"Speech synthesis canceled: {cancellation_details.reason}"
                print(self.status_message)
            elif result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                with self.lock:
                    self.status_message = f"Speech synthesis failed with reason: {result.reason}"
                print(self.status_message)
        except Exception as e:
            with self.lock:
                self.status_message = f"Speech synthesis exception: {e}"
            print(self.status_message)
        finally:
            synthesis_complete.set()

    @staticmethod
    def clean_text(text: str):
        return ''.join(char for char in text if re.match(r'[\w\s\.,!?\'":;()<>\-]', char))