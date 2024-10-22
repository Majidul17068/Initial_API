import uuid
import re
import os
import ssl
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
from datetime import datetime
from models.conversation import Conversation
from services.speech_service import SpeechService
from services.groq_service import GroqService
from services.question_data import incident_questions, accident_questions
from services.ui_helpers import display_chat_message
from services.ui_helpers import add_custom_css
from database import MongoDBClient
import threading
from datetime import datetime
import time
import streamlit as st  
from dotenv import load_dotenv


load_dotenv()

class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.speech_service = SpeechService(self)
        self.groq_service = GroqService()
        self.db_client = MongoDBClient()

    def create_new_conversation(self):
        """Creates a new conversation and assigns a unique ID."""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = Conversation(conversation_id)
        return conversation_id

    def start_conversation(self, conversation_id):
        """Initializes the conversation and determines the scenario type."""
        self.conversation_id = conversation_id
        conversation = self.conversations.get(conversation_id)
        welcome_prompt = f"Hi {conversation.reporting_person}, Welcome to the Care Home Incident and Accident Reporting System."
        self._add_message(conversation, "system", welcome_prompt, "system_message")
        self.speech_service.synthesize_speech(welcome_prompt)
        sad_welcome = f"I'm sorry to hear that there's been an event involving {conversation.resident_name}. Let's gather the details to ensure proper care and follow-up."
        self._add_message(conversation, "system", sad_welcome, "system_message")
        self.speech_service.synthesize_speech(sad_welcome)
        self._ask_scenario_type(conversation_id)

    def _ask_scenario_type(self, conversation_id):
        """Asks the user about the scenario type."""
        conversation = self.conversations.get(conversation_id)
        prompt = "Did the event result in any physical injury or harm to a person (even if minor, like a scratch)? Please say 'yes' or 'no'."
        # prompt = 'yes or no'
        self._add_message(conversation, "system", prompt, "question", "Q0")
        self.speech_service.synthesize_speech(prompt)
        
        user_response = self.capture_user_response(15, skip_grammar_check=True)
        self._add_message(conversation, "user", user_response, "answer", "Q0")

        if "no" in user_response.lower():
            scenario_message = "Let's start with questions about the incident."
            self.speech_service.synthesize_speech(scenario_message)
            self._add_message(conversation, "system", scenario_message, "system_message")
            self._initialize_conversation(conversation_id, "incident", incident_questions)
            
        elif "yes" in user_response.lower():
            scenario_message = "Let's start with questions about the accident."
            self.speech_service.synthesize_speech(scenario_message)
            self._add_message(conversation, "system", scenario_message, "system_message")
            self._initialize_conversation(conversation_id, "accident", accident_questions)
            
        else:
            error_prompt = "Please say 'yes' or 'no' to continue."
            self._add_message(conversation, "system", error_prompt, "system_message")
            self.speech_service.synthesize_speech(error_prompt)
            self._ask_scenario_type(conversation_id)

    def _initialize_conversation(self, conversation_id, scenario_type, questions):
        """Initializes the scenario type and prepares for event type selection via UI."""
        conversation = self.conversations.get(conversation_id)
        conversation.scenario_type = scenario_type
        conversation.questions = questions
        conversation.current_question_index = -1  
        event_type_options = [
            "Absconding", "Behaviour","Environmental","Fall","IPC related","Missing person","Medication","Near miss", "Physical Assault",
            "Self harm", "Skin integrity", "Others"
        ]

        conversation.event_type_options = event_type_options

        event_type_prompt = "Please select the type of event from the options below."
        self._add_message(conversation, "system", event_type_prompt, "question", "Q1")
        self.speech_service.synthesize_speech(event_type_prompt)

        conversation.waiting_for_event_type_selection = True
        
    def notification(self, conversation_id):
        
        conversation = self.conversations.get(conversation_id)
        # Get the SendGrid API key from environment variables
        SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

        # Check if the API key is available
        if not SENDGRID_API_KEY:
            raise ValueError("SENDGRID_API_KEY environment variable is not set. Please check your .env file.")

        ssl._create_default_https_context = ssl._create_default_https_context

        # Set of emails to send to
        recipient_info = {
            
            'majidulislam17068@gmail.com': 'Mazid',
            'est.med.74@gmail.com': 'Esteban'
        }
        
        incident_date = conversation.created_at
        incident_date_str = incident_date.strftime("%Y-%m-%d %H:%M:%S")
        summary = conversation.scenario_summary
        refined_summary = f"{summary}"

        # Set dynamic data for the email
        base_dynamic_data = {
            
            'type': conversation.scenario_type,
            'reporting_person': conversation.reporting_person,
            'incident_id': conversation.conversation_id,
            'incident_date': incident_date_str,
            'report_sumary': refined_summary
        }

        for email, manager_name in recipient_info.items():
            # Set dynamic data for the email, including the personalized manager name
            dynamic_data = base_dynamic_data.copy()  # Copy the base data to avoid overwriting
            dynamic_data['manager_name'] = manager_name  # Personalize manager name

            # Create the email message and assign the template ID
            message = Mail(
                from_email='mislam@tulip-tech.com',
                to_emails=To(email)
            )
            
            # Assign the template ID
            message.template_id = 'd-e97c8a529800421599dfdcf120d70d03'
            
            # Pass dynamic template data
            message.dynamic_template_data = dynamic_data

            try:
                # Send the email using SendGrid API client
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                response = sg.send(message)
                
                # Log the response from the SendGrid API
                print(f"Email sent to {email}")
                print(f"Status Code: {response.status_code}")
                print(f"Response Body: {response.body.decode() if response.body else 'No content'}")
                print(f"Response Headers: {response.headers}")

            except Exception as e:
                # Catch and display any errors that occur
                print(f"An error occurred while sending email to {email}: {str(e)}")
        


    def proceed_to_next_question(self, conversation_id):
        """Handles moving to the next question."""
        conversation = self.conversations.get(conversation_id)
        conversation.current_question_index += 1
        if conversation.current_question_index == len(conversation.questions):
            self.finalize_conversation(conversation_id)
            time.sleep(10)
            updated_summary_flag = False
            self.notify_manager(conversation_id, updated_summary_flag)
            return
        self.ask_current_question(conversation_id)

    def ask_current_question(self, conversation_id):
        """Asks the current question and validates the response."""
        conversation = self.conversations.get(conversation_id)
        current_question = conversation.questions[conversation.current_question_index]
        self._add_message(conversation, "system", current_question, "question", f"Q{conversation.current_question_index + 1}")
        self.speech_service.synthesize_speech(current_question)

        while True:
            user_response = self.capture_user_response(120, skip_grammar_check=False)
            if current_question.lower() == "when did the event happen?" and not self.validate_response_time(user_response):
                error_invalid_time = "Please include a specific time, such as '3 pm', 'yesterday', or 'last night'."
                self._add_message(conversation, "system", error_invalid_time, "system_message")
                self.speech_service.synthesize_speech(error_invalid_time)
                continue
            
            if self.needs_validation_location(current_question) and not self.validate_response_location(user_response):
                error_prompt_location = "Please specify a location or place."
                self._add_message(conversation, "system", error_prompt_location, "system_message")
                self.speech_service.synthesize_speech(error_prompt_location)
                continue

            if self.needs_validation_informed(current_question) and not self.validate_response_name_date(current_question,user_response):
                error_prompt_informed = "Please include a date and name of the person who was informed (for example: We informed the resident's son, Mark on 24th of October 2024 at 15:35)"
                self._add_message(conversation, "system", error_prompt_informed, "system_message")
                self.speech_service.synthesize_speech(error_prompt_informed)
                continue

            if user_response:
                conversation.responses[current_question] = user_response
                self._add_message(conversation, "user", user_response, "answer", f"Q{conversation.current_question_index + 1}")
                break

            error_prompt = "I didn't catch that. Could you please repeat?"
            self._add_message(conversation, "system", error_prompt, "system_message")
            self.speech_service.synthesize_speech(error_prompt)

        self.proceed_to_next_question(conversation_id)

    def needs_validation_informed(self, question):
        validation_keywords = ["Please include a date and name of the person who was informed"]
        return any(keyword in question for keyword in validation_keywords)
    
    def needs_validation_location(self, question):
        validation_keywords = ["Where did the event take place?"]
        return any(keyword in question for keyword in validation_keywords)

    def validate_response_name_date(self, question, response):
        if "Please include a date and name of the person who was informed (for example: We informed the resident's son, Mark on 24th of October 2024 at 15:35)" in question:
            name_pattern = r"\b([A-Z][a-z]+ [A-Z][a-z]*|[A-Z][a-z]+)\b"
            date_pattern = r"\b(?:\d{1,2}(?:st|nd|rd|th)?)\s?(?:of\s)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s\d{4}\b"
            time_pattern = r"\b\d{1,2}(:\d{2})?\s?(am|pm|AM|PM)?\b|\b\d{2}:\d{2}\b"

            name_match = re.search(name_pattern, response)
            date_match = re.search(date_pattern, response)
            time_match = re.search(time_pattern, response)
            
            return bool(name_match) or bool(date_match) or bool(time_match)
        return True

    def validate_response_time(self, response):
        """Validate if the response contains a recognizable time or period."""
        time_patterns = [
            r'\b\d{2}:\d{2}\b',  
            r'\b\d{1,2}(:\d{2})?\s?(am|pm)\b',
            r'\b(yesterday|today|last night|morning|afternoon|evening)\b',
        ]
        for pattern in time_patterns:
            if re.search(pattern, response.lower()):
                return True
        return False
    
    def validate_response_location(self, response):
        """Validate if the response contains a recognizable location or place."""
        place_patterns = [
            r'\b(hospital|clinic|home|street|building|park|school|office|restaurant|bedroom|garden)\b',
            r'\broom\s\d{1,3}\b', 
            r'\bstation\b',
            r'\broad\b'
        ]
        
        for pattern in place_patterns:
            if re.search(pattern, response.lower()):
                return True
        return False

    def capture_user_response(self, max_duration_seconds: int, skip_grammar_check=False):
        recognized_text = self.speech_service.start_continuous_recognition(max_duration_seconds, silence_threshold=2)
    
        if recognized_text:
            if skip_grammar_check:
                display_chat_message(is_user=True, message_text=f"{recognized_text}")
                return recognized_text
            else:
                corrected_text = self.groq_service.check_grammar(recognized_text)
                display_chat_message(is_user=True, message_text=f"{corrected_text}")
                return corrected_text
        return ""

    def _add_message(self, conversation, sender, text, message_type, question_id=None):
        message = {"sender": sender, "text": text, "timestamp": datetime.utcnow(), "message_type": message_type}
        if question_id:
            message["question_id"] = question_id
        conversation.messages.append(message)
        
    
    def display_status(self, type, message):
        # conversation_id =  st.session_state.get('conversation_id')
        conversation = self.conversations.get(self.conversation_id)
        self._add_message(conversation, type, message, 'status')
        if(type == 'info'):
            st.info(message)
        elif(type == 'error'):
            st.error(message)
        elif(type == 'warning'):
            st.warning(message)
        elif(type == 'success'):
            st.success(message)
            

    def notify_manager(self, conversation_id, flag):
        """Handles notifying the manager based on user response."""
        if flag:
            prompt = "Would you like me to notify the manager with updated summary?"
        else:
            prompt = "Would you like to notify the manager with this event summary?"
            
        self._add_message(self.conversations[conversation_id], "system", prompt, "system_message")
        self.speech_service.synthesize_speech(prompt)
        
        user_response = self.capture_user_response(15, skip_grammar_check=True)

        if "yes" in user_response.lower():
            response_text = "Manager has been notified."
            self.notification(conversation_id)
        else:
            response_text = "Manager hasn't been notified."
        
        self._add_message(self.conversations[conversation_id], "system", response_text, "system_message")
        self.speech_service.synthesize_speech(response_text) 

    def finalize_conversation(self, conversation_id):
        """Finalizes the conversation with summary and saves it."""
        conversation = self.conversations.get(conversation_id)
        summary = self.groq_service.summarize_scenario(conversation.responses, conversation.scenario_type,conversation.event_type)

        with st.spinner("Processing the event summary..."):
            summary_prompt = "Thank you for filling out the form, here is a summary of the event..."
            conversation.messages.append({
                "sender": "system",
                "text": summary_prompt,
                "timestamp": datetime.utcnow(),
                "message_type": "system_message"
            })
            self.speech_service.synthesize_speech(summary_prompt)

            display_chat_message(is_user=False, message_text=f"{summary}")

            conversation.scenario_summary = summary
            conversation.updated_at = datetime.utcnow()
        
        if "Current_Summary" not in st.session_state:
            st.session_state['Current_Summary'] = conversation.scenario_summary
            
        st.button("Edit Summary", on_click=lambda: update_summary(st.session_state['Current_Summary']))
        
        def update_summary(summary):
            if "recent_summary" not in st.session_state:
                st.session_state['recent_summary'] = summary
            if "Updated_Summary" not in st.session_state:
                st.session_state['Updated_Summary'] = ''
            self.render_previous_conversation()
            if "text_area_updated" not in st.session_state:
                st.session_state['text_area_updated'] = st.session_state['recent_summary']
            # st.text_area(
            #     "Edit the summary:", 
            #     value=st.session_state['text_area_updated'], 
            #     key='Updated_Summary_TextArea',
            #     height=500,
            #     on_change=self.display_updated_summary
            # )
            with st.form(key='summary_form'):
                st.text_area(
                "Edit the summary:", 
                value=st.session_state['text_area_updated'], 
                key='Updated_Summary_TextArea',
                height=500
                )
                st.form_submit_button(label='Update Summary', on_click=lambda: self.display_updated_summary())
            
        self.save_conversation_to_db(conversation_id)
        

    def display_updated_summary(self):
        """Display the updated summary when the text area changes."""
        conversation_id = self.conversation_id 
        add_custom_css()
        conversation = self.conversations.get(conversation_id)
        selected_event_results = st.session_state.get('Updated_Summary_TextArea')
        st.session_state['Updated_Summary'] = selected_event_results
        conversation.summary_edited = True
        self.render_previous_conversation()
        st.success("Summary updated successfully!")
        display_chat_message(is_user=False, message_text=f"{st.session_state['Updated_Summary']}")
        self._add_message(self.conversations[conversation_id], "user", st.session_state['Updated_Summary'], "Updated Summary")
        conversation.scenario_summary = st.session_state['Updated_Summary']
        updated_summary = True
        self.save_conversation_to_db(conversation_id)
        self.notify_manager(conversation_id, updated_summary)
        
        
    
    def save_conversation_to_db(self, conversation_id):
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return

        # Check if the summary has been edited
        if conversation.summary_edited:
            try:
                conversations_collection = self.db_client.db["conversations"]
                # Update only the updated_summary field if required
                conversations_collection.update_one(
                    {"conversation_id": conversation.conversation_id},
                    {"$set": {"summary": conversation.scenario_summary}}
                )
                print(f"Updated summary for conversation {conversation_id} saved to MongoDB.")
            except Exception as e:
                print(f"Error updating summary in MongoDB: {e}")
        else:
            #Save the initial summary and conversation details
            data = {
                "conversation_id": conversation.conversation_id,
                "scenario_type": conversation.scenario_type,
                "resident_id": conversation.resident_id,
                "resident_name": conversation.resident_name,
                "event_type": conversation.event_type,
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
    
    def render_previous_conversation(self):
        conversation = self.conversations.get(self.conversation_id)
        for message in conversation.messages:
            if(message['sender'] not in ('user', 'system')):
                type = message['sender']
            
                if(type == 'info'):
                    st.info(message["text"])
                elif(type == 'error'):
                    st.error(message["text"])
                elif(type == 'warning'):
                    st.warning(message["text"])
                elif(type == 'success'):
                    st.success(message["text"])
            else:
                display_chat_message(is_user=(message["sender"] == "user"), message_text=message["text"])
    
    
