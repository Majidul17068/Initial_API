from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.conversation_manager import ConversationManager
import logging
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()
conversation_manager = ConversationManager()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        response_data = conversation_manager.handle_question(
            conversation_id, user_response.question, user_response.response
        )

        return {
            "next_question": response_data.get("next_question"),
            "analysis": response_data.get("analysis"),
            "summary": response_data.get("summary"),
            "corrected_response": response_data.get("corrected_response"),
        }
    except ValueError as ve:
        logger.error(f"Error: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))

@app.post("/stop-conversation/{conversation_id}")
def stop_conversation(conversation_id: str):
    """Stop a conversation."""
    try:
        conversation_manager.stop_conversation(conversation_id)
        return {"message": "Conversation stopped successfully."}
    except ValueError as ve:
        logger.error(f"Error: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
