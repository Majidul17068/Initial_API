import uuid
import re
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
        """Creates a new conversation and assigns a unique ID."""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = Conversation(conversation_id)
        return conversation_id

    def start_conversation(self, conversation_id):
        """Initializes the conversation and determines the scenario type."""
        conversation = self.conversations.get(conversation_id)

        welcome_prompt = "Welcome to the Care Home Incident and Accident Reporting System."
        self._add_message(conversation, "system", welcome_prompt, "system_message")
        self.speech_service.synthesize_speech(welcome_prompt)

        sad_welcome = f"I'm sorry to hear that there's been an incident involving {conversation.resident_name}. Let's gather the details to ensure proper care and follow-up."
        self._add_message(conversation, "system", sad_welcome, "system_message")
        self.speech_service.synthesize_speech(sad_welcome)

        self._ask_scenario_type(conversation_id)

    def _ask_scenario_type(self, conversation_id):
        """Asks the user about the scenario type."""
        conversation = self.conversations.get(conversation_id)
        prompt = "Did the event result in any physical injury or harm to a person (even if minor, like a scratch)? Please say 'yes' or 'no'."
        self._add_message(conversation, "system", prompt, "question", "Q0")
        self.speech_service.synthesize_speech(prompt)

        user_response = self.capture_user_response(15, skip_grammar_check=True)
        self._add_message(conversation, "user", user_response, "answer", "Q0")

        if "no" in user_response.lower():
            self._initialize_conversation(conversation_id, "incident", incident_questions)
        elif "yes" in user_response.lower():
            self._initialize_conversation(conversation_id, "accident", accident_questions)
        else:
            error_prompt = "Please say 'yes' or 'no' to continue."
            self._add_message(conversation, "system", error_prompt, "system_message")
            self.speech_service.synthesize_speech(error_prompt)
            self._ask_scenario_type(conversation_id)

    def notify_manager(self, conversation_id):
        """Handles notifying the manager based on user response."""
        prompt = "Would you like me to notify the manager?"
        self._add_message(self.conversations[conversation_id], "system", prompt, "system_message")
        self.speech_service.synthesize_speech(prompt)

        user_response = self.capture_user_response(15, skip_grammar_check=True)
        
        if "yes" in user_response.lower():
            response_text = "Manager has been notified."
        else: 
            response_text = "Manager hasn't been notified."
        
        self._add_message(self.conversations[conversation_id], "system", response_text, "system_message")
        self.speech_service.synthesize_speech(response_text)

    def _initialize_conversation(self, conversation_id, scenario_type, questions):
        """Initializes the scenario type and starts the questions."""
        conversation = self.conversations[conversation_id]
        conversation.scenario_type = scenario_type
        conversation.questions = questions
        intro_text = f"Let's start with questions about the {scenario_type}."
        self._add_message(conversation, "system", intro_text, "system_message")
        self.speech_service.synthesize_speech(intro_text)
        self.proceed_to_next_question(conversation_id)

    def proceed_to_next_question(self, conversation_id):
        """Handles moving to the next question."""
        conversation = self.conversations.get(conversation_id)
        conversation.current_question_index += 1

        if conversation.current_question_index == len(conversation.questions):
            self.notify_manager(conversation_id)
            self.finalize_conversation(conversation_id)
            return

        self.ask_current_question(conversation_id)

    def ask_current_question(self, conversation_id):
        """Asks the current question and handles the response."""
        conversation = self.conversations.get(conversation_id)
        current_question = conversation.questions[conversation.current_question_index]
        self._add_message(conversation, "system", current_question, "question", f"Q{conversation.current_question_index + 1}")
        self.speech_service.synthesize_speech(current_question)

        for attempt in range(3):
            user_response = self.capture_user_response(120, skip_grammar_check=False)
            if user_response:
                self._add_message(conversation, "user", user_response, "answer", f"Q{conversation.current_question_index + 1}")

                if current_question.lower() == "when did it happen?":
                    if self.validate_response_time(user_response):
                        conversation.responses[current_question] = user_response
                        break
                    else:
                        error_invalid_time = "Please include a specific time such as '3 pm', 'yesterday', or 'last night'."
                        self._add_message(conversation, "system", error_invalid_time, "system_message")
                        self.speech_service.synthesize_speech(error_invalid_time)

                elif self.needs_validation(current_question):
                    if self.validate_response(current_question, user_response):
                        conversation.responses[current_question] = user_response
                        break
                    else:
                        error_prompt_validation = "Please select one of the provided options. If you are not sure, please say 'Other'."
                        self._add_message(conversation, "system", error_prompt_validation, "system_message")
                        self.speech_service.synthesize_speech(error_prompt_validation)

                elif self.needs_validation_informed(current_question):
                    if self.validate_response_name_date(current_question, user_response):
                        conversation.responses[current_question] = user_response
                        break
                    else:
                        error_prompt_informed = "Please include a name, date, and who was informed e.g: We informed the social worker named Sajib on 24th October 2024."
                        self._add_message(conversation, "system", error_prompt_informed, "system_message")
                        self.speech_service.synthesize_speech(error_prompt_informed)

                else:
                    conversation.responses[current_question] = user_response
                    break
            else:
                error_prompt = "I didn't catch that. Could you please repeat?"
                self._add_message(conversation, "system", error_prompt, "system_message")
                self.speech_service.synthesize_speech(error_prompt)

        if not conversation.responses.get(current_question):
            error_prompt = "Sorry, we couldn't capture your response. Let's move to the next question."
            self._add_message(conversation, "system", error_prompt, "system_message")
            self.speech_service.synthesize_speech(error_prompt)

        self.proceed_to_next_question(conversation_id)

    def needs_validation(self, question):
        validation_keywords = ["Can you tell me the type of event from the following options?"]
        return any(keyword in question for keyword in validation_keywords)

    def needs_validation_informed(self, question):
        validation_keywords = ["Please state name and date if any of the following parties has been informed:"]
        return any(keyword in question for keyword in validation_keywords)

    def validate_response(self, question, response):
        if "Can you tell me the type of event from the following options?" in question:
            valid_options = ["fall", "behaviour", "medication", "skin integrity", "environmental", "absconding",
                             "physical assault", "self harm", "ipc related", "near miss", "missing person", "others", "other"]
            return any(option in response.lower() for option in valid_options)
        return True

    def validate_response_name_date(self, question, response):
        if "Please state name and date if any of the following parties has been informed:" in question:
            name_pattern = r"\b([A-Z][a-z]+ [A-Z][a-z]*|[A-Z][a-z]+)\b"
            date_pattern = r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s\d{4}\b)"
            parties_informed = ["family", "next of kin", "advocate", "social worker", "case manager",
                                "adult safeguarding", "cqc", "police", "gp", "riddor"]

            name_match = re.search(name_pattern, response)
            date_match = re.search(date_pattern, response)
            role_match = any(role in response.lower() for role in parties_informed)

            return bool(name_match) and bool(date_match) and role_match
        return True

    def validate_response_time(self, response):
        """Validate if the response contains a recognizable time or period."""
        time_patterns = [
            r'\b\d{1,2}(:\d{2})?\s?(AM|PM|am|pm)\b',  # Matches times like '3 PM' or '12:30 am'
            r'\b(yesterday|today|last night|evening|morning|afternoon)\b',  # Matches relative expressions
            r'\b\d{1,2}(th|st|nd|rd)\b',  # Matches date expressions like '3rd', '21st', etc.
        ]
        for pattern in time_patterns:
            if re.search(pattern, response):
                return True
        return False

    def capture_user_response(self, max_duration_seconds: int, skip_grammar_check=False):
        recognized_text = self.speech_service.start_continuous_recognition(max_duration_seconds, silence_threshold=2)

        if recognized_text:
            display_chat_message(is_user=True, message_text=recognized_text)
            return recognized_text if skip_grammar_check else self.groq_service.check_grammar(recognized_text)
        return ""

    def _add_message(self, conversation, sender, text, message_type, question_id=None):
        message = {"sender": sender, "text": text, "timestamp": datetime.utcnow(), "message_type": message_type}
        if question_id:
            message["question_id"] = question_id
        conversation.messages.append(message)

    def finalize_conversation(self, conversation_id):
        conversation = self.conversations.get(conversation_id)
        summary_prompt = "Thank you for filling out the form, here is a summary of the event..."
        self._add_message(conversation, "system", summary_prompt, "system_message")
        self.speech_service.synthesize_speech(summary_prompt)

        summary = self.groq_service.summarize_scenario(conversation.responses, conversation.scenario_type)
        display_chat_message(is_user=False, message_text=f"{summary}")

        conversation.scenario_summary = summary
        conversation.updated_at = datetime.utcnow()
        self.save_conversation_to_db(conversation_id)

    def save_conversation_to_db(self, conversation_id):
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
        self.speech_service.stop_speech_recognition()
        print(f"Conversation {conversation_id} stopped.")