import streamlit as st
import time
from services.conversation_manager import ConversationManager
from services.speech_service import add_custom_css

# Function to start a new conversation
def start_conversation():
    conversation_manager = ConversationManager()
    conversation_id = conversation_manager.create_new_conversation
    conversation_manager.start_conversation(conversation_id)
    st.session_state['conversation_manager'] = conversation_manager
    st.session_state['conversation_id'] = conversation_id
    st.session_state['conversation_active'] = True

# Function to stop the current conversation
def stop_conversation():
    if st.session_state.get('conversation_active'):
        conversation_manager = st.session_state.get('conversation_manager')
        conversation_id = st.session_state.get('conversation_id')

        if conversation_manager and conversation_id:
            conversation_manager.stop_conversation(conversation_id)
            del st.session_state['conversation_manager']
            del st.session_state['conversation_id']
            st.session_state['conversation_active'] = False
            st.success("Conversation stopped.")
        else:
            st.warning("No active conversation to stop.")

def main():
    with st.sidebar:
        st.title("Care Home Incident and Accident Reporting System")
    
    # Provide the Logo
    st.image("logo.png", caption="Care Home AI Agent", width=200)
    
    add_custom_css()
    # Buttons to start and stop the conversation
    if st.button("Start Conversation") and not st.session_state.get('conversation_active'):
        start_conversation()
    add_custom_css()
    if st.button("Stop Conversation") and st.session_state.get('conversation_active'):
        stop_conversation()

if __name__ == "__main__":
    # Initialize session state to store conversation_manager and conversation_id between reruns
    if 'conversation_manager' not in st.session_state:
        st.session_state['conversation_manager'] = None
    
    if 'conversation_id' not in st.session_state:
        st.session_state['conversation_id'] = None

    if 'conversation_active' not in st.session_state:
        st.session_state['conversation_active'] = False
    
    main()