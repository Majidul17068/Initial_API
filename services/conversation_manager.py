import uuid
import json
import os
import time
import threading
from models.conversation import Conversation
from services.speech_service import SpeechService
from services.groq_service import GroqService
from datetime import datetime
from services.question_data import incident_questions, accident_questions
from services.ui_helpers import display_chat_message

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

    def proceed_to_next_question(self, conversation_id):
        """Handles the flow of moving to the next question."""
        conversation = self.conversations.get(conversation_id)
        conversation.current_question_index += 1  # Increment index unconditionally

        if conversation.current_question_index >= len(conversation.questions):
            # End of questions - proceed to summarization and confirmation steps
            summary_prompt = "Thank you for filling up the form, here is a summary of the event..."
            # Synthesize speech and display the summary prompt
            self.speech_service.synthesize_speech(summary_prompt)

            summary = self.groq_service.summarize_scenario(conversation.responses, conversation.scenario_type)
            # Synthesize speech and display the summary
            #self.speech_service.synthesize_speech(summary)
            display_chat_message(is_user=False, message_text=f"{summary}")

            conversation.scenario_summary = summary
            self.save_conversation_to_json(conversation_id)
        else:
            # Ask the current question
            current_question = conversation.questions[conversation.current_question_index]
            # Synthesize speech and display the question
            self.speech_service.synthesize_speech(current_question)

            # Proceed to capture user response
            for attempt in range(3):
                user_response = self.capture_user_response(60, skip_grammar_check=False)
                if user_response:
                    # Validate response for specific questions
                    if self.needs_validation(current_question):
                        if self.validate_response(current_question, user_response):
                            conversation.responses[current_question] = user_response
                            break
                        else:
                            error_prompt = "Please select one of the provided options, if you are not sure, please say 'Other'."
                            # Synthesize speech and display the error prompt
                            self.speech_service.synthesize_speech(error_prompt)
                    else:
                        conversation.responses[current_question] = user_response
                        break
                else:
                    error_prompt = "I didn't catch that. Could you please repeat?"
                    # Synthesize speech and display the error prompt
                    self.speech_service.synthesize_speech(error_prompt)

            if not conversation.responses.get(current_question):
                error_prompt = "Sorry, we couldn't capture your response. Let's move to the next question."
                # Synthesize speech and display the error prompt
                self.speech_service.synthesize_speech(error_prompt)

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
            valid_options = [
                "fall", "behaviour", "medication", "skin integrity",
                "environmental", "absconding", "physical assault",
                "self harm", "ipc related", "near miss",
                "missing person", "others"
            ]
            return any(option in response.lower() for option in valid_options)
        return True

    def capture_user_response(self, max_duration_seconds: int, skip_grammar_check=False):
        """Captures user response with specified timeout."""
        stop_event = threading.Event()
        self.speech_service.recognized_text = ""

        # Set dynamic timeouts
        segment_timeout = 10000
        initial_timeout = 15000
        self.speech_service.set_dynamic_timeouts(segment_timeout, initial_timeout)

        # Start speech recognition
        self.speech_service.start_continuous_recognition()

        # Wait for response
        start_time = time.time()
        recognized_text = ""
        last_speech_time = start_time
        silence_threshold = 2 
        while time.time() - start_time < max_duration_seconds:
            with self.speech_service.lock:
                if self.speech_service.recognized_text:
                    recognized_text += self.speech_service.recognized_text + " "
                    self.speech_service.recognized_text = ""
                    last_speech_time = time.time()
                elif time.time() - last_speech_time > silence_threshold and recognized_text:
                    # If there's been silence for more than the threshold and we have some text, end capture
                    break
            time.sleep(0.1)

        self.speech_service.stop_speech_recognition()

        # Process recognized text
        if recognized_text:
            recognized_text = recognized_text.strip()
            if skip_grammar_check:
                display_chat_message(is_user=True, message_text=recognized_text)
                return recognized_text
            else:
                corrected_text = self.groq_service.check_grammar(recognized_text)
                display_chat_message(is_user=True, message_text=corrected_text)
                return corrected_text
        else:
            return ""

    def save_conversation_to_json(self, conversation_id):
        """Saves the conversation to a JSON file."""
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"conversation_{conversation_id}_{timestamp}.json"
        filepath = os.path.join("conversations", filename)
        os.makedirs("conversations", exist_ok=True)
        data = {
            "conversation_id": conversation.conversation_id,
            "scenario_type": conversation.scenario_type,
            "questions_and_responses": conversation.responses,
            "summary": conversation.scenario_summary,
            "timestamp": timestamp
        }
        try:
            with open(filepath, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            print(f"Conversation saved to {filepath}")
        except Exception as e:
            print(f"Error saving conversation to JSON: {e}")

    def start_conversation(self, conversation_id):
        """Initializes the conversation and determines the type."""
        welcome_prompt = "Welcome to the Care Home Incident and Accident Reporting System."
        # Synthesize speech and display the welcome prompt
        self.speech_service.synthesize_speech(welcome_prompt)
        self._ask_scenario_type(conversation_id)

    def _ask_scenario_type(self, conversation_id):
        """Asks the user about the scenario type."""
        prompt = "Did the event result in any physical injury or harm to a person (even if minor, like a scratch)? Please say 'yes' or 'no'."
        # Synthesize speech and display the prompt
        self.speech_service.synthesize_speech(prompt)
        user_response = self.capture_user_response(15, skip_grammar_check=True)
        if "no" in user_response.lower():
            self._initialize_conversation(conversation_id, "incident", incident_questions)
        elif "yes" in user_response.lower():
            self._initialize_conversation(conversation_id, "accident", accident_questions)
        else:
            error_prompt = "Please say 'yes' or 'no' to continue."
            # Synthesize speech and display the error prompt
            self.speech_service.synthesize_speech(error_prompt)
            self._ask_scenario_type(conversation_id)

    def _initialize_conversation(self, conversation_id, scenario_type, questions):
        """Initializes the conversation with the selected scenario."""
        conversation = self.conversations[conversation_id]
        conversation.scenario_type = scenario_type
        conversation.questions = questions
        intro_text = f"Let's start with questions about the {scenario_type}."
        # Synthesize speech and display the introduction text
        self.speech_service.synthesize_speech(intro_text)
        self.proceed_to_next_question(conversation_id)

    def stop_conversation(self, conversation_id):
        """Ends the conversation and cleans up resources."""
        self.speech_service.stop_speech_recognition()
        print(f"Conversation {conversation_id} stopped.")