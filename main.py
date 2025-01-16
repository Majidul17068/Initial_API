from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.conversation_manager import ConversationManager
import logging

# Initialize app and services
app = FastAPI()
conversation_manager = ConversationManager()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust for frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request models
class UserResponse(BaseModel):
    question: str
    response: str

@app.post("/start-conversation")
def start_conversation():
    """Start a new conversation and return the first question."""
    try:
        conversation_id = conversation_manager.create_new_conversation()
        first_question = conversation_manager.start_conversation(conversation_id)
        return {
            "conversation_id": conversation_id,
            "first_question": first_question
        }
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start conversation.")

@app.post("/ask-question/{conversation_id}")
def ask_question(conversation_id: str, user_response: UserResponse):
    """Process a user's response and return the next question, analysis, or summary."""
    try:
        next_question, analysis_message, summary = conversation_manager.handle_question(
            conversation_id, user_response.question, user_response.response
        )

        response_data = {"next_question": next_question}
        if analysis_message:
            response_data["analysis"] = analysis_message
        if summary:
            response_data["summary"] = summary

        return response_data
    except ValueError as ve:
        logger.error(f"Error: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.post("/stop-conversation/{conversation_id}")
def stop_conversation(conversation_id: str):
    """Stop a conversation."""
    try:
        conversation_manager.stop_conversation(conversation_id)
        return {"message": "Conversation stopped successfully."}
    except ValueError as ve:
        logger.error(f"Error: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
