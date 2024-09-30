import threading
import time
import azure.cognitiveservices.speech as speechsdk
import os
import streamlit as st
import re
from services.groq_service import GroqService
from services.ui_helpers import display_chat_message

class SpeechService:
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION")
        )
        # Audio config for recognizer (microphone input)
        self.audio_config_recognizer = speechsdk.audio.AudioConfig(use_default_microphone=True)
        # Audio config for synthesizer (default speaker output)
        self.audio_config_synthesizer = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        self.speech_config.speech_synthesis_voice_name = "en-GB-BellaNeural"
        self.speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=self.audio_config_synthesizer
        )
        self.speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=self.audio_config_recognizer
        )
        self.groq_service = GroqService()
        self.recognized_text = ""
        self.status_message = ""
        self.lock = threading.Lock()  # To protect shared resources

        # Event handlers for continuous recognition
        self.speech_recognizer.recognized.connect(self.recognized_handler)
        self.speech_recognizer.session_started.connect(self.session_started_handler)
        self.speech_recognizer.session_stopped.connect(self.session_stopped_handler)
        self.speech_recognizer.canceled.connect(self.canceled_handler)

    def set_dynamic_timeouts(self, segment_timeout: int, initial_timeout: int):
        """Sets the dynamic timeouts for the speech recognizer."""
        self.speech_config.set_property(
            speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(segment_timeout))
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(initial_timeout))

    def recognized_handler(self, evt):
        """Handler to process recognized speech."""
        recognized_text = evt.result.text.strip()
        if recognized_text:
            with self.lock:
                self.recognized_text = recognized_text

    def session_started_handler(self, evt):
        """Handler for session started events."""
        with self.lock:
            self.status_message = "Speech recognition started."

    def session_stopped_handler(self, evt):
        """Handler for session stopped events."""
        with self.lock:
            self.status_message = "Speech recognition stopped."

    def canceled_handler(self, evt):
        """Handler to process canceled recognition events."""
        with self.lock:
            self.status_message = f"Speech recognition canceled: {evt.result.reason}"
        self.stop_speech_recognition()

    def start_continuous_recognition(self):
        """Start continuous speech recognition."""
        try:
            with self.lock:
                self.recognized_text = ""
                self.status_message = ""
            self.speech_recognizer.start_continuous_recognition()
            st.info("Speech recognition started.")
        except Exception as e:
            with self.lock:
                self.status_message = f"Error starting continuous recognition: {e}"

    def stop_speech_recognition(self):
        """Stop continuous speech recognition."""
        try:
            self.speech_recognizer.stop_continuous_recognition()
            st.info("Speech recognition stopped.")
        except Exception as e:
            with self.lock:
                self.status_message = f"Error stopping speech recognition: {e}"

    def synthesize_speech(self, text: str):
        cleaned_text = self.clean_text(text)
        
        # Display the text immediately
        display_chat_message(is_user=False, message_text=cleaned_text)
        
        # Event to signal when speech synthesis is complete
        synthesis_complete = threading.Event()
        
        # Start speech synthesis in a separate thread
        synthesis_thread = threading.Thread(
            target=self._synthesize_speech_thread, 
            args=(cleaned_text, synthesis_complete)
        )
        synthesis_thread.start()
        
        # Wait for speech synthesis to complete without blocking the main thread
        while not synthesis_complete.is_set():
            time.sleep(0.1)  # Sleep briefly to yield control to Streamlit
        
        return True

    def _synthesize_speech_thread(self, text: str, synthesis_complete):
        try:
            result = self.speech_synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                with self.lock:
                    self.status_message = f"Speech synthesis canceled: {cancellation_details.reason}"
            elif result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                with self.lock:
                    self.status_message = f"Speech synthesis failed with reason: {result.reason}"
        except Exception as e:
            with self.lock:
                self.status_message = f"Speech synthesis exception: {e}"
        finally:
            # Signal that synthesis is complete
            synthesis_complete.set()

    @staticmethod
    def clean_text(text: str):
        """Remove special characters from text."""
        return ''.join(char for char in text if re.match(r'[\w\s\.,!?\'":;()-]', char))