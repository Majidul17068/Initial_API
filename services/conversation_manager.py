import os
import json
import uuid
from services.groq_service import GroqService

class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.history_dir = "./conversation_history"
        self.groq_service = GroqService()

        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    def create_new_conversation(self):
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = {
            "responses": {},
            "analysis": None,
            "summary": None,
            "injury_questions": False  # Track if injury-specific questions are active
        }
        return conversation_id

    def get_conversation(self, conversation_id):
        """Retrieve an active conversation by its ID."""
        return self.conversations.get(conversation_id)

    def save_conversation(self, conversation_id):
        """Save a conversation to a JSON file."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found.")
        file_path = os.path.join(self.history_dir, f"{conversation_id}.json")
        with open(file_path, "w") as file:
            json.dump(conversation, file, indent=4)

    def start_conversation(self, conversation_id):
        """Start a conversation and return the first question."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found.")
        return "Please select the type of event from the options below."

    def handle_question(self, conversation_id, question, response):
        """Handle questions and responses during the conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found.")

        # Correct grammar using GroqService
        corrected_response = self.groq_service.check_grammar(response)

        # Print debug messages
        print(f"User Response Received: {response}")
        print(f"Corrected Response: {corrected_response}")

        # Save corrected response
        conversation["responses"][question] = corrected_response
        self.save_conversation(conversation_id)

        initial_questions = [
            "Please select the type of event from the options below.",
            "Please provide the name of the staff member who has any information regarding the event.",
            "Where did the event take place?",
            "When did the event happen?",
            "Were there any witnesses?",
            "Please provide details of the event.",
        ]

        if question in initial_questions:
            current_index = initial_questions.index(question)
            if current_index < len(initial_questions) - 1:
                return {
                    "next_question": initial_questions[current_index + 1],
                    "analysis": None,
                    "summary": None,
                    "corrected_response": corrected_response
                }

            if question == "Please provide details of the event.":
                analysis_result = self.groq_service.event_analysis(corrected_response)
                conversation["analysis"] = analysis_result
                conversation["scenario_type"] = analysis_result["classification"]

                analysis_message = (
                    "\U0001F4CB **Event Classification**:\n\n"
                    + ("\U0001F6A8 Accident" if analysis_result["classification"] == "accident" else "⚡ Incident") + "\n\n"
                    + f"**Reasoning**: {analysis_result['classification_reason']}\n\n"
                    + "\U0001F3E5 **Injury Risk Analysis**:\n\n"
                    + ("⚠️ High chance of physical injury\n" if analysis_result["has_injury"] else "✓ No significant injury risk detected\n")
                    + f"**Risk Level**: {analysis_result['likelihood']}%\n\n"
                    + f"**Assessment**: {analysis_result['reasoning']}\n\n"
                )

                self.save_conversation(conversation_id)
                if analysis_result["has_injury"]:
                    return {
                        "next_question": "Did the patient sustain a physical injury as a result of the event?",
                        "analysis": analysis_message,
                        "summary": None,
                        "corrected_response": corrected_response
                    }
                return {
                    "next_question": "Please provide details of any immediate action taken.",
                    "analysis": analysis_message,
                    "summary": None,
                    "corrected_response": corrected_response
                }

        if question == "Did the patient sustain a physical injury as a result of the event?":
            if corrected_response.lower() == "yes":
                conversation["injury_questions"] = True
                return {
                    "next_question": "Please specify the size of the injury.",
                    "analysis": None,
                    "summary": None,
                    "corrected_response": corrected_response
                }
            return {
                "next_question": "Please provide details of any immediate action taken.",
                "analysis": None,
                "summary": None,
                "corrected_response": corrected_response
            }

        if conversation.get("injury_questions", False):
            if question == "Please specify the size of the injury.":
                return {
                    "next_question": "Please specify the location of the injury.",
                    "analysis": None,
                    "summary": None,
                    "corrected_response": corrected_response
                }
            if question == "Please specify the location of the injury.":
                conversation["injury_questions"] = False  # Reset flow
                return {
                    "next_question": "Please provide details of any immediate action taken.",
                    "analysis": None,
                    "summary": None,
                    "corrected_response": corrected_response
                }

        remaining_questions = [
            "Please provide details of any immediate action taken.",
            "Would you like to add any vital observations?",
            "Please describe any recovery action taken and by whom?",
            "Please include a date and name of the person who was informed.",
            "Thank you for filling out the form. Here is a summary of the event."
        ]

        if question in remaining_questions:
            current_index = remaining_questions.index(question)
            if current_index < len(remaining_questions) - 1:
                return {
                    "next_question": remaining_questions[current_index + 1],
                    "analysis": None,
                    "summary": None,
                    "corrected_response": corrected_response
                }
            if question == "Thank you for filling out the form. Here is a summary of the event.":
                summary = self.groq_service.summarize_scenario(
                    responses=conversation["responses"],
                    resident_name="Resident Name",
                    scenario_type=conversation.get("scenario_type", "incident"),
                    event_type="Event Type",
                    staff="Staff Name"
                )
                conversation["summary"] = summary
                self.save_conversation(conversation_id)
                return {
                    "next_question": None,
                    "analysis": None,
                    "summary": summary,  # Ensure summary is passed to frontend
                    "corrected_response": corrected_response
                    
                }

        return {
            "next_question": None,
            "analysis": None,
            "summary": None,
            "corrected_response": corrected_response
        }

    def stop_conversation(self, conversation_id):
        """Stop a conversation and remove it from active memory."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        else:
            raise ValueError("Conversation not found.")
