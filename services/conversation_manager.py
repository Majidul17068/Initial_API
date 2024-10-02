# services/conversation_manager.py

import uuid
from datetime import datetime
from models.conversation import Conversation
from services.speech_service import SpeechService
from services.groq_service import GroqService
from services.question_data import incident_questions, accident_questions
from services.ui_helpers import display_chat_message
from database import MongoDBClient

class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.speech_service = SpeechService()
        self.groq_service = GroqService()
        self.db_client = MongoDBClient()

    def create_new_conversation(self):
        """Creates a new conversation state and assigns a unique ID."""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = Conversation(conversation_id)
        return conversation_id

    def start_conversation(self, conversation_id):
        """Initializes the conversation and determines the type."""
        conversation = self.conversations.get(conversation_id)
        welcome_prompt = f"Hi {conversation.reporting_person}, Welcome to the Care Home Incident and Accident Reporting System."

        conversation.messages.append({
            "sender": "system",
            "text": welcome_prompt,
            "timestamp": datetime.utcnow(),
            "message_type": "system_message"
        })
        self.speech_service.synthesize_speech(welcome_prompt)

        sad_welcome = f"I'm sorry to hear that there's been an event involving resident name {conversation.resident_name}. Let's gather the details to ensure proper care and follow-up."

        conversation.messages.append({
            "sender": "system",
            "text": sad_welcome,
            "timestamp": datetime.utcnow(),
            "message_type": "system_message"
        })
        self.speech_service.synthesize_speech(sad_welcome)
        self._ask_scenario_type(conversation_id)

    def _ask_scenario_type(self, conversation_id):
        """Asks the user about the scenario type."""
        conversation = self.conversations.get(conversation_id)
        prompt = "Did the event result in any physical injury or harm to a person (even if minor, like a scratch)? Please say 'yes' or 'no'."
        conversation.messages.append({
            "sender": "system",
            "text": prompt,
            "timestamp": datetime.utcnow(),
            "message_type": "question",
            "question_id": "Q0"
        })
        self.speech_service.synthesize_speech(prompt)
        user_response = self.capture_user_response(15, skip_grammar_check=True)
        conversation.messages.append({
            "sender": "user",
            "text": user_response,
            "timestamp": datetime.utcnow(),
            "message_type": "answer",
            "question_id": "Q0"
        })
        if "no" in user_response.lower():
            self._initialize_conversation(conversation_id, "incident", incident_questions)
        elif "yes" in user_response.lower():
            self._initialize_conversation(conversation_id, "accident", accident_questions)
        else:
            error_prompt = "Please say 'yes' or 'no' to continue."
            conversation.messages.append({
                "sender": "system",
                "text": error_prompt,
                "timestamp": datetime.utcnow(),
                "message_type": "system_message"
            })
            self.speech_service.synthesize_speech(error_prompt)
            self._ask_scenario_type(conversation_id)

    def _initialize_conversation(self, conversation_id, scenario_type, questions):
        """Initializes the conversation with the selected scenario."""
        conversation = self.conversations[conversation_id]
        conversation.scenario_type = scenario_type
        conversation.questions = questions
        intro_text = f"Let's start with questions about the {scenario_type}."
        conversation.messages.append({
            "sender": "system",
            "text": intro_text,
            "timestamp": datetime.utcnow(),
            "message_type": "system_message"
        })
        self.speech_service.synthesize_speech(intro_text)
        self.proceed_to_next_question(conversation_id)

    def proceed_to_next_question(self, conversation_id):
        """Handles the flow of moving to the next question."""
        conversation = self.conversations.get(conversation_id)
        conversation.current_question_index += 1

        if conversation.current_question_index >= len(conversation.questions):
            self.finalize_conversation(conversation_id)
        else:
            self.ask_current_question(conversation_id)

    def ask_current_question(self, conversation_id):
        """Asks the current question and handles the response."""
        conversation = self.conversations.get(conversation_id)
        current_question = conversation.questions[conversation.current_question_index]
        conversation.messages.append({
            "sender": "system",
            "text": current_question,
            "timestamp": datetime.utcnow(),
            "message_type": "question",
            "question_id": f"Q{conversation.current_question_index + 1}"
        })
        self.speech_service.synthesize_speech(current_question)

        for attempt in range(3):
            user_response = self.capture_user_response(120, skip_grammar_check=False)
            if user_response:
                conversation.messages.append({
                    "sender": "user",
                    "text": user_response,
                    "timestamp": datetime.utcnow(),
                    "message_type": "answer",
                    "question_id": f"Q{conversation.current_question_index + 1}"
                })
                if self.needs_validation(current_question):
                    if self.validate_response(current_question, user_response):
                        conversation.responses[current_question] = user_response
                        break
                    else:
                        error_prompt = "Please select one of the provided options, if you are not sure, please say 'Other'."
                        conversation.messages.append({
                            "sender": "system",
                            "text": error_prompt,
                            "timestamp": datetime.utcnow(),
                            "message_type": "system_message"
                        })
                        self.speech_service.synthesize_speech(error_prompt)
                else:
                    conversation.responses[current_question] = user_response
                    break
            else:
                error_prompt = "I didn't catch that. Could you please repeat?"
                conversation.messages.append({
                    "sender": "system",
                    "text": error_prompt,
                    "timestamp": datetime.utcnow(),
                    "message_type": "system_message"
                })
                self.speech_service.synthesize_speech(error_prompt)

        if not conversation.responses.get(current_question):
            error_prompt = "Sorry, we couldn't capture your response. Let's move to the next question."
            conversation.messages.append({
                "sender": "system",
                "text": error_prompt,
                "timestamp": datetime.utcnow(),
                "message_type": "system_message"
            })
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
                "fall", "behaviour", "behavior", "medication", "skin integrity",
                "environmental", "absconding", "physical assault",
                "self harm", "ipc related", "near miss",
                "missing person", "others", "other"
            ]
            return any(option in response.lower() for option in valid_options)
        return True

    def capture_user_response(self, max_duration_seconds: int, skip_grammar_check=False):
        """Captures user response with specified timeout and silence detection."""
        recognized_text = self.speech_service.start_continuous_recognition(max_duration_seconds, silence_threshold=2)

        if recognized_text:
            if skip_grammar_check:
                display_chat_message(is_user=True, message_text=recognized_text)
                return recognized_text
            else:
                corrected_text = self.groq_service.check_grammar(recognized_text)
                display_chat_message(is_user=True, message_text=corrected_text)
                return corrected_text
        else:
            return ""

    def finalize_conversation(self, conversation_id):
        """Finalizes the conversation with summary and saves it."""
        conversation = self.conversations.get(conversation_id)
        summary_prompt = "Thank you for filling out the form, here is a summary of the event..."
        conversation.messages.append({
            "sender": "system",
            "text": summary_prompt,
            "timestamp": datetime.utcnow(),
            "message_type": "system_message"
        })
        self.speech_service.synthesize_speech(summary_prompt)

        summary = self.groq_service.summarize_scenario(conversation.responses, conversation.scenario_type)

        display_chat_message(is_user=False, message_text=f"{summary}")

        conversation.scenario_summary = summary
        conversation.updated_at = datetime.utcnow()
        self.save_conversation_to_db(conversation_id)

    def save_conversation_to_db(self, conversation_id):
        """Saves the conversation to MongoDB."""
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return

        data = {
            "conversation_id": conversation.conversation_id,
            "scenario_type": conversation.scenario_type,
            "resident_id": conversation.resident_id,
            "resident_name": conversation.resident_name,
            "reporting_agent_id": conversation.reporting_person_id,
            "reporting_agent": conversation.reporting_person,
            "messages": conversation.messages,
            "summary": conversation.scenario_summary,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }

        try:
            conversations_collection = self.db_client.db["conversations"]
            conversations_collection.insert_one(data)
            print(f"Conversation {conversation_id} saved to MongoDB.")
        except Exception as e:
            print(f"Error saving conversation to MongoDB: {e}")

    def stop_conversation(self, conversation_id):
        """Ends the conversation and cleans up resources."""
        self.speech_service.stop_speech_recognition()
        print(f"Conversation {conversation_id} stopped.")
