# app.py
from fastapi import FastAPI, BackgroundTasks
from services.conversation_manager import ConversationManager

app = FastAPI()

# Initialize the conversation manager (can be shared across multiple requests)
conversation_manager = ConversationManager()

@app.post("/start_voice_conversation")
async def start_voice_conversation(background_tasks: BackgroundTasks):
    try:
        conversation_id = conversation_manager.create_new_conversation
        background_tasks.add_task(conversation_manager.start_conversation, conversation_id)
        return {"message": "Voice conversation started", "conversation_id": conversation_id}
    
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
