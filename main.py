import streamlit as st
from services.conversation_manager import ConversationManager
from services.ui_helpers import add_custom_css

def start_conversation():
    conversation_manager = ConversationManager()
    conversation_id = conversation_manager.create_new_conversation
    conversation_manager.start_conversation(conversation_id)
    st.session_state['conversation_manager'] = conversation_manager
    st.session_state['conversation_id'] = conversation_id
    st.session_state['conversation_active'] = True

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

    status_placeholder = st.empty()

    # Buttons to start and stop the conversation
    if st.button("Start Conversation") and not st.session_state.get('conversation_active'):
        start_conversation()
    if st.button("Stop Conversation") and st.session_state.get('conversation_active'):
        stop_conversation()

    conversation_manager = st.session_state.get('conversation_manager')
    if conversation_manager is not None:
        speech_service = conversation_manager.speech_service
        with speech_service.lock:
            status_message = speech_service.status_message
            speech_service.status_message = ""  # Clear after reading
        if status_message:
            status_placeholder.error(status_message)

if __name__ == "__main__":
    if 'conversation_active' not in st.session_state:
        st.session_state['conversation_active'] = False

    main()