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
    def __init__(self, conversation_id):
        self.conversations = {}
        self.speech_service = SpeechService(self, conversation_id)
        self.groq_service = GroqService()
        self.db_client = MongoDBClient()
        self.create_new_conversation(conversation_id)
    

    def get_user_data(self, username):
        """
        Returns the data associated with a username if the username exists in user_data.
        
        Args:
            username (str): The username to look up in the dictionary.
        
        Returns:
            str: The data associated with the username if found, or an error message if not.
        """
        user_data = {
        "sibtain@langdalecarehomes.co.uk": "Sibtain",
        "amaan@langdalecarehomes.co.uk": "Amaan",
        "sajjad@langdalecarehomes.co.uk": "Sajjad",
        "neemat@langdalecarehomes.co.uk" : "Neemat",
        "zishan@langdalecarehomes.co.uk" : "Zishan",
        "Sajib" : "Sajib",
        "Lucalicata@test.com" : "Luca",
        "Esteban@test.com" : "Esteban" }
        
        # Check if the username is a key in the dictionary
        if username in user_data:
            return user_data[username]
        else:
            return " "
    def create_new_conversation(self,conversation_id):
        """Creates a new conversation and assigns a unique ID."""
        self.conversations[conversation_id] = Conversation(conversation_id)
        return conversation_id

    def start_conversation(self, conversation_id):
        """Initializes the conversation and determines the scenario type, including resident selection."""
        self.conversation_id = conversation_id
        conversation = self.conversations.get(conversation_id)
        
        # Display the initial welcome prompt
        name = st.session_state.get("username","User")
        updated_name = self.get_user_data(name)
        
        welcome_prompt = f"Hello {updated_name}, Welcome to the Care Home Incident and Accident Reporting System."
        self._add_message(conversation, "system", welcome_prompt, "system_message", "Q0")
        
        self.speech_service.synthesize_speech(welcome_prompt)
        time.sleep(1)

        selct_resident="Please select resident from the list"
        self._add_message(conversation, "system", selct_resident, "system_message", "Q0")
        self._add_message_db(conversation, "system", selct_resident, "system_message", "Q0")
        self.speech_service.synthesize_speech(selct_resident)
        
        # Call resident selection process here
        add_custom_css
        self._select_resident(conversation_id)

    def _select_resident(self, conversation_id):
        """
        Function to display a selectbox to select resident_id and resident_name,
        and store the selected values in the conversation object.
        """
        conversation = self.conversations.get(conversation_id)
        residents = self.fetch_residents()

        if not residents:
            error_message = "No residents found in the database. Please check the database."
            self._add_message(conversation, "system", error_message, "system_message")
            self.speech_service.synthesize_speech(error_message)
            return

        # Convert residents to a dictionary for the selectbox
        resident_options = {
            res['resident_name']: res
            for res in residents
        }

        st.session_state['resident_options'] = resident_options

        def on_resident_change(resident_options):
            selected_resident_key = st.session_state.get('selected_resident_key')
            if selected_resident_key and selected_resident_key != "Select a resident...":
                selected_resident = resident_options[selected_resident_key]
                conversation.resident_id = selected_resident['resident_id']
                conversation.resident_name = selected_resident['resident_name']
                # Add the selected resident details to the conversation messages
                selected_resident_message = f"Selected Resident: {conversation.resident_name}"
                self._add_message(conversation, "user", selected_resident_message, "user", "Q0")
                self._add_message_db(conversation, "user", selected_resident_message, "user", "Q0")
                self.render_previous_conversation()
                add_custom_css()
                self._proceed_after_resident_selection(conversation_id)
            else:
                pass

        st.selectbox(
            "Please select a resident:",
            options=["Select a resident..."] + list(resident_options.keys()),
            key='selected_resident_key',
            on_change=lambda: on_resident_change(resident_options)
        )

    def _proceed_after_resident_selection(self, conversation_id):
        """Proceed with conversation after resident selection."""
        conversation = self.conversations.get(conversation_id)
        apology_prompt = f"I'm sorry to hear that there's been an event involving {conversation.resident_name}. Let's gather the details to ensure proper care and follow-up."
        self._add_message(conversation, "system", apology_prompt, "system_message")
        self.speech_service.synthesize_speech(apology_prompt)
        time.sleep(1)
        
        # Proceed to the next step of asking scenario type
        add_custom_css()
        time.sleep(1)
        #self._ask_scenario_type(conversation_id)
        self._initialize_conversation(conversation_id, "incident", incident_questions)

    def fetch_residents(self):
        """
        Returns a list of residents from a predefined custom list.
        """
        resident_list = [
            {"resident_id": "5d90b9ff-1294-4200-8b75-2ea86949a487", "resident_name": "JESSIE COOPER"},
            {"resident_id": "25f00dc7-e379-4e40-8382-8b98db4e1ed4", "resident_name": "JENNIFER GREEN"},
            {"resident_id": "ca761e17-8ce7-48aa-80f6-e56bc699fbef", "resident_name": "ANITA BUSWELL"},
            {"resident_id": "2e72e712-635a-40e5-ac47-f588033e130a", "resident_name": "ARTHUR CAPENHURST"},
            {"resident_id": "0e519c4a-65fe-4be0-8c6d-17fa48e7fdb6", "resident_name": "JASHVANTI KAKAD"},
            {"resident_id": "8766c05b-12db-4979-b025-9c708c77dee7", "resident_name": "JUNE THORPE"},
            {"resident_id": "bb4fa59f-347a-4c42-95bc-86db7354691a", "resident_name": "ZAID TELADIA"},
            {"resident_id": "03792b04-4137-4ba6-bd1c-1994a9e745c2", "resident_name": "LONNIE CALHOUN"},
            {"resident_id": "a1b9c3e5-725c-442d-9a42-a07deb815f14", "resident_name": "ASTRID DEACON"},
            {"resident_id": "17125fe2-f402-41e0-b873-69ee9067c996", "resident_name": "MICHAEL TRUSLOVE"},
            {"resident_id": "cd8819f8-3583-40bb-aeee-06465da48074", "resident_name": "ANTHONY HENSON"},
            {"resident_id": "19c65ff5-9472-4441-809e-5afc142a8d85", "resident_name": "ADRIAN EVERITT"},
            {"resident_id": "e0435ffa-b8d6-4ad2-b7e4-6758b5b45c75", "resident_name": "MARK WHEELER"},
            {"resident_id": "fc7edd26-27fe-4ef8-bea3-f22465a065cd", "resident_name": "PETER BRYAN"},
            {"resident_id": "f6625e7e-27ba-4500-8fd6-c3ba73c44eb6", "resident_name": "ANNE SANSOME"},
            {"resident_id": "e1855203-c76b-4aa9-aafc-e33417569f46", "resident_name": "PATRICIA CHILDS"},
            {"resident_id": "a28c0ddd-5d41-4da3-8d02-0c6e86c54057", "resident_name": "SYLVIA WALKER"},
            {"resident_id": "ea0b6e2d-4d73-4a7c-acf8-f7c170e0711f", "resident_name": "BEVERLEY BUNNEY"},
            {"resident_id": "48d7b433-e60b-4283-a516-005753e8f6b4", "resident_name": "PATRICK STAFFORD"},
            {"resident_id": "7b73d6d9-5c53-4119-b403-3ad0aec06e49", "resident_name": "ROSEMARY BENNETT"},
            {"resident_id": "7606bee4-eeed-4a8c-9bae-2b551ac6ae48", "resident_name": "PATRICIA GARDINER"},
            {"resident_id": "976e0204-c40b-4480-ba1d-a41d10fa4843", "resident_name": "PAULA JEYNES"},
            {"resident_id": "72dee3da-bb21-40c4-af60-fbe4d50cba53", "resident_name": "BRENDA VERNON"},
            {"resident_id": "353e5803-5f22-4e6f-9c84-bea224b792ca", "resident_name": "DAVID BRANT"},
            {"resident_id": "bba04f76-8be6-4572-99d1-0a1fbde111ba", "resident_name": "DENNIS NICHOLLS"},
            {"resident_id": "b4795a2b-7c37-405c-b04c-93ba6289c88b", "resident_name": "DEREK PALMER"},
            {"resident_id": "96ef54a0-8518-4fcd-96d6-6a07cd74d172", "resident_name": "DAVID STAMERS"},
            {"resident_id": "f4e06367-f150-485b-b5b8-3144b58b6675", "resident_name": "EILEEN BEDDER"},
            {"resident_id": "991ee120-bb55-46fc-8fc3-8b5ad5fc2ce8", "resident_name": "ELIZABETH WALKER"},
            {"resident_id": "f5910ece-5055-4bc9-8e1f-ff4ef9de1698", "resident_name": "FRANCINE QUILITZ"},
            {"resident_id": "b1c547e2-6c36-4c78-a1e6-e5471d652fa2", "resident_name": "MICHAEL ROWELL"},
            {"resident_id": "5cac1ecb-62bf-40e2-a47e-93b5e7ee3c28", "resident_name": "ARTHUR BREWARD"},
            {"resident_id": "4ac7e816-60fb-4275-8697-0a80a6352049", "resident_name": "ROSEMARY WHITE"},
            {"resident_id": "f775fff5-a5ba-4b79-b536-f1a204be7c39", "resident_name": "JOHN PAYNE"},
            {"resident_id": "f51ef4df-fb9e-4f02-9258-3346475044f2", "resident_name": "IVY ORTON"},
            {"resident_id": "3d3c1c28-43f3-4b85-ac4a-51881cc887dd", "resident_name": "GLENDA WALKER"},
            {"resident_id": "6b995e22-3aae-45f2-b79c-3767e884eb14", "resident_name": "DAVID SAUNDERS"},
            {"resident_id": "3a577994-c7b8-4ba5-8b80-b725403091ec", "resident_name": "BRIAN SULLIVAN"},
            {"resident_id": "cf8ab9cc-4ceb-44ff-823b-54899bb51c87", "resident_name": "ALISON DIBB"},
        ]
        return resident_list

    def _ask_scenario_type(self, conversation_id):
        """Asks the user about the scenario type."""
        conversation = self.conversations.get(conversation_id)
        prompt = "Did the event result in any physical injury or harm to a person (even if minor, like a scratch)? Please say 'yes' or 'no'."
        # prompt = 'yes or no'
        self._add_message(conversation, "system", prompt, "question", "Q1")
        self.speech_service.synthesize_speech(prompt)
        
        user_response = self.capture_user_response(15, skip_grammar_check=True)
        self._add_message(conversation, "user", user_response, "answer", "Q1")
        

        if "no" in user_response.lower():
            scenario_message = "Let's start with questions about the incident."
            self.speech_service.synthesize_speech(scenario_message)
            time.sleep(1)
            self._add_message(conversation, "system", scenario_message, "system_message")
            self._add_message_db(conversation, "system", prompt, "question", "Q1")
            self._add_message_db(conversation, "user", user_response, "answer", "Q1")
            self._initialize_conversation(conversation_id, "incident", incident_questions)
            
        elif "yes" in user_response.lower():
            scenario_message = "Let's start with questions about the accident."
            self.speech_service.synthesize_speech(scenario_message)
            time.sleep(1)
            self._add_message(conversation, "system", scenario_message, "system_message")
            self._add_message_db(conversation, "system", prompt, "question", "Q1")
            self._add_message_db(conversation, "user", user_response, "answer", "Q1")
            self._initialize_conversation(conversation_id, "accident", accident_questions)
            
        else:
            error_prompt = "Please say 'yes' or 'no' to continue."
            self._add_message(conversation, "system", error_prompt, "system_message")
            self.speech_service.synthesize_speech(error_prompt)
            time.sleep(1)
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
        self._add_message(conversation, "system", event_type_prompt, "question", "Q2")
        self._add_message_db(conversation, "system", event_type_prompt, "question", "Q2")

        self.speech_service.synthesize_speech(event_type_prompt)

        # Set waiting_for_event_type_selection to True
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
            dynamic_data = base_dynamic_data.copy()  
            dynamic_data['manager_name'] = manager_name  

            # Create the email message and assign the template ID
            message = Mail(
                from_email='reporting@tulip-tech.com',
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
            
            #updated_summary_flag = False
            #self.notify_manager(conversation_id, updated_summary_flag)
            return
        self.ask_current_question(conversation_id)

    def ask_current_question(self, conversation_id):
        """Asks the current question and validates the response."""
        conversation = self.conversations.get(conversation_id)
        
        current_question = conversation.questions[conversation.current_question_index]
        self._add_message(conversation, "system", current_question, "question", f"Q{conversation.current_question_index + 1}")
        self._add_message_db(conversation, "system", current_question, "question", f"Q{3 + conversation.counter}")
        conversation.counter = conversation.counter + 1
        self.speech_service.synthesize_speech(current_question)
        
        while True:
            user_response = self.capture_user_response(120, skip_grammar_check=False)
            
            if current_question == "Please provide details of the event":
                # Analyze the event for injury risk
                analysis_result = self.groq_service.event_analysis(user_response)
                
                conversation.responses[current_question] = user_response
                conversation.injury_analysis = analysis_result
                conversation.scenario_type = analysis_result['classification']
                
                status_level = "warning" if analysis_result['has_injury'] else "info"
                analysis_message = (
                    f"📋 Event Classification.\n\n"
                    f"📋 Based on the event details it can be classified as {'🚨 Accident' if analysis_result['classification'] == 'accident' else '⚡ Incident\n'}\n"
                    f"Reasoning: {analysis_result['classification_reason']}\n\n"
                    f"🏥 Injury Risk Analysis:\n\n"
                    f"{'⚠️ From the event details there is a high chance of physical injury\n' if analysis_result['has_injury'] else '✓ No significant injury risk detected\n'}\n"
                    f"Risk Level: {analysis_result['likelihood']}%\n\n"
                    f"Assessment: {analysis_result['reasoning']}\n\n"
                )
                
                # Display analysis results
                time.sleep(3)
                self._add_message(conversation, "user", user_response, "answer")
                self.display_status("warning", analysis_message)
                self._add_message_db(conversation, status_level, analysis_message, "analysis", f"Q{3 + conversation.counter}")
                
                if analysis_result['has_injury']:
                    if analysis_result['injury_mentioned']:
                        self._ask_injury_size(conversation_id)
                    else:
                        self._ask_injury_confirmation(conversation_id)
                    return
                
                self.proceed_to_next_question(conversation_id)
                return

            # Regular question handling remains the same
            if current_question.lower() == "when did the event happen?" and not self.validate_response_time(user_response):
                error_invalid_time = "Please include a specific time, such as '3 pm', 'yesterday', or 'last night'."
                self._add_message(conversation, "system", error_invalid_time, "system_message")
                self.speech_service.synthesize_speech(error_invalid_time)
                continue
            

            if user_response:
                conversation.responses[current_question] = user_response
                self._add_message(conversation, "user", user_response, "answer", f"Q{conversation.current_question_index + 1}")
                self._add_message_db(conversation, "user", user_response, "answer", f"Q{3 + conversation.counter}")
                break

            error_prompt = "I didn't catch that. Could you please repeat?"
            self._add_message(conversation, "system", error_prompt, "system_message")
            self.speech_service.synthesize_speech(error_prompt)

        self.proceed_to_next_question(conversation_id)
        
    def _ask_injury_confirmation(self, conversation_id):
        """Ask if patient sustained physical injury"""
        conversation = self.conversations.get(conversation_id)
        
        injury_question = "Did the patient sustain a physical injury as a result of the event?"
        self._add_message(conversation, "system", injury_question, "question")
        self.speech_service.synthesize_speech(injury_question)
        
        injury_response = self.capture_user_response(15, skip_grammar_check=True)
        self._add_message(conversation, "user", injury_response, "answer")
        self._add_message_db(conversation, "user", injury_response, "answer", f"Q{3 + conversation.counter}")
        
        if "yes" in injury_response.lower():
            conversation.scenario_type = "accident"
            self.display_status("warning", "Based on the injury, this event will be classified as an accident.")
            self._ask_injury_size(conversation_id)
        else:
            self.proceed_to_next_question(conversation_id)
            
    def _ask_injury_size(self, conversation_id):
        """Ask about injury size using selectbox"""
        conversation = self.conversations.get(conversation_id)
        
        if 'injury_size_selected' not in st.session_state:
            st.session_state['injury_size_selected'] = False
            
        def on_size_change():
            selected_size = st.session_state.get('selected_injury_size')
            if selected_size:
                st.session_state['injury_size_selected'] = True
                conversation.injury_size = selected_size
                self._add_message(conversation, "user", selected_size, "answer")
                self._add_message_db(conversation, "user", selected_size, "answer", f"Q{3 + conversation.counter}")
                
                self.render_previous_conversation()
                add_custom_css()
                self._ask_injury_location(conversation_id)

        if not st.session_state['injury_size_selected']:
            size_question = "Please specify the size of the injury"
            self._add_message(conversation, "system", size_question, "question")
            self._add_message_db(conversation, "system", size_question, "question", f"Q{3 + conversation.counter}")
            self.speech_service.synthesize_speech(size_question)
            
            injury_sizes = ["Small", "Medium", "Large"]
            st.selectbox(
                "Select injury size:",
                options=injury_sizes,
                key='selected_injury_size',
                on_change=on_size_change
            )
            return

               
    def _ask_injury_details(self, conversation_id):
        """Handles the injury size and location questions."""
        conversation = self.conversations.get(conversation_id)
        self.display_status("warning","Thank you for confirming the injury. Based on this information, the incident will be classified as an accident.")
        conversation.scenario_type = "accident"

        if 'injury_size_selected' not in st.session_state:
            st.session_state['injury_size_selected'] = False
            
        def on_size_change():
            selected_size = st.session_state.get('selected_injury_size')
            if selected_size:
                st.session_state['injury_size_selected'] = True
                conversation.injury_size = selected_size
                self._add_message(conversation, "user", selected_size, "answer")
                self._add_message_db(conversation, "user", selected_size, "answer", f"Q{3 + conversation.counter}")
                
                self.render_previous_conversation()
                add_custom_css()
                self._ask_injury_location(conversation_id)

        # Show selectbox if size not selected yet
        if not st.session_state['injury_size_selected']:
            size_question = "Please specify the size of the injury"
            self._add_message(conversation, "system", size_question, "question")
            self._add_message_db(conversation, "system", size_question, "question", f"Q{3 + conversation.counter}")
            self.speech_service.synthesize_speech(size_question)
            
            # Create selectbox for injury size
            injury_sizes = ["Small", "Medium", "Large"]
            st.selectbox(
                "Select injury size:",
                options=injury_sizes,
                key='selected_injury_size',
                on_change=on_size_change
            )
            return 
            
    def _ask_injury_location(self, conversation_id):
        """Ask about injury location"""
        conversation = self.conversations.get(conversation_id)
        
        location_question = "Please specify the location of the injury"
        self._add_message(conversation, "system", location_question, "question")
        self._add_message_db(conversation, "system", location_question, "question", f"Q{3 + conversation.counter}")
        self.speech_service.synthesize_speech(location_question)
        
        location_response = self.capture_user_response(20, skip_grammar_check=False)
        
        if location_response:
            self._add_message(conversation, "user", location_response, "answer")
            self._add_message_db(conversation, "user", location_response, "answer", f"Q{3 + conversation.counter}")
            conversation.injury_location = location_response
            
            # Clear injury size selection state
            if 'injury_size_selected' in st.session_state:
                del st.session_state['injury_size_selected']
            
            # Continue with normal question flow
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
            # r'\b(hospital|clinic|home|street|building|park|school|office|restaurant|bedroom|garden)\b',
            # r'\broom\s\d{1,3}\b', 
            # r'\bstation\b',
            # r'\broad\b'
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

    def _add_message_db(self, conversation, sender, text, message_type, question_id=None):
        message = {"sender": sender, "text": text,  "message_type": message_type}
        if question_id:
            message["question_id"] = question_id
        conversation.message_db.append(message)

        
    
    def display_status(self, type, message):
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
        conversation = self.conversations.get(conversation_id)
        """Handles notifying the manager based on user response."""
        if flag:
            prompt = "Would you like me to notify the manager with updated summary?"
        else:
            prompt = "Would you like to notify the manager with this event summary?"
            
        self._add_message(self.conversations[conversation_id], "system", prompt, "system_message")
        self._add_message_db(self.conversations[conversation_id], "system", prompt, "system_message", f"Q{ 3 + conversation.counter}")
        self.speech_service.synthesize_speech(prompt)
        
        user_response = self.capture_user_response(15, skip_grammar_check=True)

        if "yes" in user_response.lower():
            response_text = "Manager has been notified."
            self.notification(conversation_id)
            
        else:
            response_text = "Manager has been notified with the updated summary"
            self.notification(conversation_id)
        
        self._add_message(self.conversations[conversation_id], "system", response_text, "system_message")
        self._add_message_db(self.conversations[conversation_id], "system", response_text, "system_message")
        self.speech_service.synthesize_speech(response_text) 
        time.sleep(1)
        final_prompt = "Thank you for completing the immediate response report, all the information provided will be stored and can be retrieved in the post incident/accident report where you would be able to add more information about the event."
        self._add_message(self.conversations[conversation_id], "system", final_prompt, "system_message")
        self.speech_service.synthesize_speech(final_prompt)

    def finalize_conversation(self, conversation_id):
        """Finalizes the conversation with summary and saves it."""
        conversation = self.conversations.get(conversation_id)

        asking_edit_response = "Would you like to edit any of your response?"
        
        self.speech_service.synthesize_speech(asking_edit_response)
        
        edit_summary_response = self.capture_user_response(15, skip_grammar_check=True)
        if "yes" in edit_summary_response.lower():
            retrived_conversation = []
            for message in conversation.messages:
                if(message['sender'] in ('user', 'system')):
                    retrived_conversation.append(f"**{message['sender'].upper()}** : {message['text']}")
            
            message_text='\n\n'.join(retrived_conversation)
            display_chat_message(is_user=False, message_text=f"{message_text}")
            if "Current_message" not in st.session_state:
                st.session_state['Current_message'] = message_text
            
            st.button("Edit reponse", on_click=lambda: update_response())
            def update_response():
                self.render_previous_conversation()
                add_custom_css()
                with st.form(key='Response_form'):
                    st.text_area(
                    "Edit the response:", 
                    value=st.session_state['Current_message'], 
                    key='Updated_response_TextArea',
                    height=500
                    )
                    st.form_submit_button(label='Update Response', on_click=lambda: display_updated_response())
                    def display_updated_response():
                        selected_event_results = st.session_state.get('Updated_response_TextArea')
                        st.session_state['Updated_response_TextArea'] = selected_event_results
                        add_custom_css()
                        self.render_previous_conversation()
                        st.success("Response updated successfully!")
                        display_chat_message(is_user=False, message_text=f"{st.session_state['Updated_response_TextArea']}")
                        self._add_message(self.conversations[conversation_id], "user", st.session_state['Updated_response_TextArea'], "Updated Response Text")
                        conversation.updated_conversation = st.session_state['Updated_response_TextArea']
                        summary = self.groq_service.summarize_scenario(st.session_state['Updated_response_TextArea'], conversation.resident_name, conversation.scenario_type, conversation.event_type, conversation.witness)

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
                        updated_summary_flag = False
                        time.sleep(10)
                        self.notify_manager(conversation_id, updated_summary_flag)
                            
                        def update_summary(summary):
                            if "recent_summary" not in st.session_state:
                                st.session_state['recent_summary'] = summary
                            if "Updated_Summary" not in st.session_state:
                                st.session_state['Updated_Summary'] = ''
                            self.render_previous_conversation()
                            if "text_area_updated" not in st.session_state:
                                st.session_state['text_area_updated'] = st.session_state['recent_summary']

                            with st.form(key='summary_form'):
                                st.text_area(
                                "Edit the summary:", 
                                value=st.session_state['text_area_updated'], 
                                key='Updated_Summary_TextArea',
                                height=500
                                )
                                st.form_submit_button(label='Update Summary', on_click=lambda: self.display_updated_summary())
                        self.save_conversation_to_db(conversation_id)
        else:
            summary = self.groq_service.summarize_scenario(conversation.responses, conversation.resident_name, conversation.scenario_type, conversation.event_type, conversation.witness)

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

                with st.form(key='summary_form'):
                    st.text_area(
                    "Edit the summary:", 
                    value=st.session_state['text_area_updated'], 
                    key='Updated_Summary_TextArea',
                    height=500
                    )
                    st.form_submit_button(label='Update Summary', on_click=lambda: self.display_updated_summary())
            self.save_conversation_to_db(conversation_id)
            time.sleep(10)
            updated_summary_flag = False
            self.notify_manager(conversation_id, updated_summary_flag)
          

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
        self._add_message_db(self.conversations[conversation_id], "user", st.session_state['Updated_Summary'], "Updated Summary")
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
            data = {
                "conversation_id": conversation.conversation_id,
                "scenario_type": conversation.scenario_type,
                "resident_id": conversation.resident_id,
                "resident_name": conversation.resident_name,
                "event_type": conversation.event_type,
                "reporting_agent_id": conversation.reporting_person_id,
                "reporting_agent": conversation.reporting_person,
                "messages": conversation.message_db,
                "Updated_Reponse": conversation.updated_conversation,
                "summary": conversation.scenario_summary,
                "post_event_completed":conversation.post_event_completed,
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
    
    
