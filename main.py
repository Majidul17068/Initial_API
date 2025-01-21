from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.conversation_manager import ConversationManager
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize conversation manager with error handling
try:
    conversation_manager = ConversationManager()
except Exception as e:
    logger.error(f"Failed to initialize ConversationManager: {e}")
    raise

class UserResponse(BaseModel):
    question: str
    response: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection if available
        if conversation_manager.redis_client:
            conversation_manager.redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected" if conversation_manager.redis_client else "fallback to memory"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/start-conversation")
async def start_conversation():
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-question/{conversation_id}")
async def ask_question(conversation_id: str, user_response: UserResponse):
    """Process a user's response and return the next question."""
    try:
        response_data = conversation_manager.handle_question(
            conversation_id, 
            user_response.question, 
            user_response.response
        )
        return response_data
    except ValueError as ve:
        logger.error(f"Value Error in ask_question: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop-conversation/{conversation_id}")
async def stop_conversation(conversation_id: str):
    """Stop a conversation and clean up resources."""
    try:
        conversation_manager.stop_conversation(conversation_id)
        return {"message": "Conversation stopped successfully"}
    except ValueError as ve:
        logger.error(f"Value Error in stop_conversation: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in stop_conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
