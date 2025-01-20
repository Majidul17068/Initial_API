import uuid
import json
import redis
import os
from services.groq_service import GroqService

class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.groq_service = GroqService()
        
        # Get Redis credentials from environment
        redis_url = os.getenv('REDIS_URL')
        redis_host = os.getenv('REDIS_HOST')
        redis_port = os.getenv('REDIS_PORT')
        redis_username = os.getenv('REDIS_USERNAME')
        redis_password = os.getenv('REDIS_PASSWORD')
        
        print("Redis Configuration:")
        print(f"Host: {redis_host}")
        print(f"Port: {redis_port}")
        print(f"Username: {redis_username}")
        
        try:
            if redis_url:
                print("Attempting to connect using REDIS_URL")
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    ssl=True,
                    ssl_cert_reqs=None
                )
            elif all([redis_host, redis_port, redis_username, redis_password]):
                print("Attempting to connect using individual credentials")
                redis_url = f"rediss://{redis_username}:{redis_password}@{redis_host}:{redis_port}"
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    ssl=True,
                    ssl_cert_reqs=None
                )
            else:
                raise ValueError("Redis credentials not properly configured")
            
            # Test the connection
            self.redis_client.ping()
            print("Successfully connected to Redis")
            self._load_conversations_from_cache()
            
        except Exception as e:
            print(f"Redis connection error: {str(e)}")
            print("Falling back to in-memory storage only")
            self.redis_client = None

    def _load_conversations_from_cache(self):
        """Load existing conversations from Redis cache."""
        if not self.redis_client:
            return
            
        try:
            cached_conversations = self.redis_client.keys('conversation:*')
            for key in cached_conversations:
                conv_id = key.decode('utf-8').split(':')[1]
                cached_data = self.redis_client.get(key)
                if cached_data:
                    self.conversations[conv_id] = json.loads(cached_data)
        except Exception as e:
            print(f"Error loading from cache: {e}")

    def _cache_conversation(self, conversation_id):
        """Cache conversation data in Redis."""
        if not self.redis_client:
            return
            
        try:
            conversation = self.get_conversation(conversation_id)
            if conversation:
                self.redis_client.set(
                    f'conversation:{conversation_id}',
                    json.dumps(conversation),
                    ex=86400  # Cache for 24 hours
                )
        except Exception as e:
            print(f"Error caching conversation: {e}")

    def create_new_conversation(self):
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = {
            "responses": {},
            "analysis": None,
            "summary": None,
            "injury_questions": False
        }
        self._cache_conversation(conversation_id)
        return conversation_id

    def get_conversation(self, conversation_id):
        """Retrieve an active conversation by its ID."""
        return self.conversations.get(conversation_id)

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
        self._cache_conversation(conversation_id)

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
                self._cache_conversation(conversation_id)

                analysis_message = (
                    "\U0001F4CB **Event Classification**:\n\n"
                    + ("\U0001F6A8 Accident" if analysis_result["classification"] == "accident" else "⚡ Incident") + "\n\n"
                    + f"**Reasoning**: {analysis_result['classification_reason']}\n\n"
                    + "\U0001F3E5 **Injury Risk Analysis**:\n\n"
                    + ("⚠️ High chance of physical injury\n" if analysis_result["has_injury"] else "✓ No significant injury risk detected\n")
                    + f"**Risk Level**: {analysis_result['likelihood']}%\n\n"
                    + f"**Assessment**: {analysis_result['reasoning']}\n\n"
                )

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
                self._cache_conversation(conversation_id)
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
                conversation["injury_questions"] = False
                self._cache_conversation(conversation_id)
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
                self._cache_conversation(conversation_id)
                return {
                    "next_question": None,
                    "analysis": None,
                    "summary": summary,
                    "corrected_response": corrected_response
                }

        return {
            "next_question": None,
            "analysis": None,
            "summary": None,
            "corrected_response": corrected_response
        }

    def stop_conversation(self, conversation_id):
        """Stop a conversation and remove it from active memory and cache."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            if self.redis_client:
                try:
                    self.redis_client.delete(f'conversation:{conversation_id}')
                except Exception as e:
                    print(f"Error deleting from cache: {e}")
        else:
            raise ValueError("Conversation not found.")
