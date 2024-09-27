import uuid
import json
import os
import time
import threading
from models.conversation import Conversation
from services.speech_service import SpeechService
from services.groq_service import GroqService
from datetime import datetime, timezone
from services.question_data import incident_questions, accident_questions
from services.speech_service import add_custom_css, display_chat_message
class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.speech_service = SpeechService()
        self.groq_service = GroqService()
    @property
    def create_new_conversation(self):
        """Creates a new conversation state and assigns a unique ID."""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = Conversation(conversation_id)
        return conversation_id
    def proceed_to_next_question(self, conversation_id, first=False):
        """Handles the flow of moving to the next question."""
        conversation = self.conversations.get(conversation_id)
        if not first:
            conversation.current_question_index += 1
        if conversation.current_question_index >= len(conversation.questions):
            # End of questions - proceed to summarization and confirmation steps
            self.speech_service.synthesize_speech("Thank you for filling up the form, here is a summary of the event...")
            summary = self.groq_service.summarize_scenario(conversation.responses, conversation.scenario_type)
            
            display_chat_message(is_user=False, message_text=f"{summary}")
            conversation.scenario_summary = summary
            self.save_conversation_to_json(conversation_id)
        else:
            # Ask the current question
            current_question = conversation.questions[conversation.current_question_index]
            self.speech_service.synthesize_speech(current_question)
            # Retry mechanism for capturing valid input
            for attempt in range(3):
                user_response = self.capture_user_response(60, skip_grammar_check=False)
                
                if user_response:
                    # Validate response for specific questions
                    if self.needs_validation(current_question):
                        if self.validate_response(current_question, user_response):
                            conversation.responses[current_question] = user_response
                            break
                        else:
                            self.speech_service.synthesize_speech("Please select one of the provided options, if you are not sure, please say 'Other' ")
                    else:
                        conversation.responses[current_question] = user_response
                        break
                else:
                    self.speech_service.synthesize_speech("I didn't catch that. Could you please repeat?")
            
            if not conversation.responses.get(current_question):
                self.speech_service.synthesize_speech("Sorry, we couldn't capture your response. Let's move to the next question.")
            
            self.proceed_to_next_question(conversation_id)


    def needs_validation(self, question):
        """Determines if a question needs validation."""
        validation_keywords = [
            "Can you tell me the type of event from the following options?"
        ]
        return any(keyword in question for keyword in validation_keywords)
    
    def validate_response(self, question, response):
        """Validates the response for specific questions."""
        if "Can you tell me the type of event from the following options?" in question:
            valid_options = [ "fall", "behaviour", "medication", "skin integrity", 
                              "environmental", "absconding", "physical assault", 
                              "self-harm", "ipc related", "near miss", 
                              "missing person", "others"]
            return any(option in response.lower() for option in valid_options)
        
        return True
    
    def capture_user_response(self, duration_seconds: int, skip_grammar_check=False):
        """Helper function to capture user response with specified timeout and perform grammar check if needed."""

        stop_event = threading.Event()
    
        self.speech_service.recognized_text = ""
    
        # Calculate and set dynamic timeouts before starting recognition
        segment_timeout = duration_seconds * 2000  
        initial_timeout = (duration_seconds + 5) * 1000 
        self.speech_service.set_dynamic_timeouts(segment_timeout, initial_timeout)
        
        # Define an event handler for recognition
        def on_recognized(evt):
            if evt.result.text:
                self.speech_service.recognized_text = evt.result.text
                stop_event.set()  
       
        handler_id = self.speech_service.speech_recognizer.recognized.connect(on_recognized)
        # Start speech recognition
        self.speech_service.start_continuous_recognition()
    
        stop_event.wait(timeout=duration_seconds)
    
        self.speech_service.stop_speech_recognition()
    
        self.speech_service.speech_recognizer.recognized.disconnect_all()
    
        # Perform grammar check on the recognized text if needed
        if self.speech_service.recognized_text:
            if skip_grammar_check:
                display_chat_message(is_user=True, message_text=self.speech_service.recognized_text)
                return self.speech_service.recognized_text
            else:
                corrected_text = self.groq_service.check_grammar(self.speech_service.recognized_text)
                display_chat_message(is_user=True, message_text=corrected_text)
                return corrected_text
        else:
            return ""
    
            
    def save_conversation_to_json(self, conversation_id):
        """Saves the conversation to a JSON file."""
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return
        # Define the file name based on the conversation ID and the current timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"conversation_{conversation_id}_{timestamp}.json"
        filepath = os.path.join("conversations", filename)
        # Ensure the conversations directory exists
        os.makedirs("conversations", exist_ok=True)
        # Structure the data to be saved
        data = {
            "conversation_id": conversation.conversation_id,
            "scenario_type": conversation.scenario_type,
            "questions_and_responses": conversation.responses,
            "summary": conversation.scenario_summary,
            "timestamp": timestamp
        }
        # Save the conversation to a JSON file
        try:
            with open(filepath, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            print(f"Conversation saved to {filepath}")
        except Exception as e:
            print(f"Error saving conversation to JSON: {e}")
    def start_conversation(self, conversation_id):
        """Initializes the conversation and determines the type (incident or accident)."""
        self.speech_service.synthesize_speech("Welcome to the Care Home Incident and Accident Reporting System.")
        self._ask_scenario_type(conversation_id)
    def _ask_scenario_type(self, conversation_id):
        """Asks the user whether the report is for an accident or an incident."""
        self.speech_service.synthesize_speech("Did the event result in any physical injury or harm to a person. (even if minor, like a scratch)?")
        user_response = self.capture_user_response(15, skip_grammar_check=False) 
        if "no" in user_response.lower():
            self._initialize_conversation(conversation_id, "incident", incident_questions)
        elif "yes" in user_response.lower():
            self._initialize_conversation(conversation_id, "accident", accident_questions)
        else:
            self.speech_service.synthesize_speech("Please say 'yes' or 'no' to continue.")
            self._ask_scenario_type(conversation_id)
    def _initialize_conversation(self, conversation_id, scenario_type, questions):
        """Initializes the scenario type and starts the questions."""
        conversation = self.conversations[conversation_id]
        conversation.scenario_type = scenario_type
        conversation.questions = questions
        intro_text = f"Let's start with questions about the {scenario_type}."
        self.speech_service.synthesize_speech(intro_text)
        self.proceed_to_next_question(conversation_id, first=True)
    def stop_conversation(self, conversation_id):
        """Ends the conversation and cleans up resources."""
        self.speech_service.stop_speech_recognition()
        print(f"Conversation {conversation_id}")