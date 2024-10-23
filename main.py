import streamlit as st
from services.conversation_manager import ConversationManager
from services.ui_helpers import add_custom_css, display_chat_message

def start_conversation():
    conversation_manager = ConversationManager()
    conversation_id = conversation_manager.create_new_conversation()
    conversation_manager.start_conversation(conversation_id)
    
    st.session_state['conversation_manager'] = conversation_manager
    st.session_state['conversation_id'] = conversation_id
    st.session_state['conversation_active'] = True
    st.session_state['event_type_confirmed'] = False
    st.session_state['event_type_first_time_went_through'] = False
    st.session_state['selected_event_type'] = None
    st.session_state['staff_name'] = ""
    st.session_state['name_confirmed'] = False
    st.session_state['corrected_name'] = ""


def stop_conversation():
    if st.session_state.get('conversation_active', False):
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

def render_previous_conversation(conversation):
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
    
def reinitialize_conversation(conversation):
    conversation_manager = st.session_state.get('conversation_manager')
    conversation_id = st.session_state.get('conversation_id')
    
    if not st.session_state.get('name_confirmed', False):
        staff_name_prompt = "Please provide the name of the staff member who has any information regarding the event."
        conversation_manager._add_message(conversation, "system", staff_name_prompt, "question", "Q2")
        conversation_manager.speech_service.synthesize_speech(staff_name_prompt)

        staff_name = conversation_manager.capture_user_response(15, skip_grammar_check=True)
        st.session_state['staff_name'] = staff_name
        conversation_manager._add_message(conversation, "user", staff_name, "question", "Q2")
        
        spelling_prompt = "If the spelling of the staff name is correct, please say 'yes' or 'no'."
        conversation_manager.speech_service.synthesize_speech(spelling_prompt)
        conversation_manager._add_message(conversation, "system", staff_name_prompt, "question", "Q2")
        
        spelling_response = conversation_manager.capture_user_response(15, skip_grammar_check=True)
        
        if "yes" in spelling_response.lower():
            st.session_state['name_confirmed'] = True
            conversation_manager._add_message(conversation, "user", staff_name, "question", "Q2")
            conversation_manager.display_status('success', "Name confirmed")
            conversation_manager.proceed_to_next_question(conversation_id)
        else:
            name_input_prompt = "Please enter the correct spelling of the staff name:"
            userresponse = 'No'
            conversation_manager._add_message(conversation, "user", userresponse, "question", "Q2")
            conversation_manager.speech_service.synthesize_speech(name_input_prompt)
            conversation_manager._add_message(conversation, "system", name_input_prompt, "question", "Q2")
            st.text_input(
                "Please enter the correct spelling of the staff name:",
                key='staff_name_input',
                on_change=lambda: confirm_name(conversation, conversation_manager, conversation_id)
            )

def confirm_name(conversation, conversation_manager, conversation_id):
    add_custom_css()
    corrected_name = st.session_state['staff_name_input']
    st.session_state['corrected_name'] = corrected_name
    st.session_state['name_confirmed'] = True
    conversation_manager._add_message(conversation, "user", corrected_name, "answer", "Q2")
    render_previous_conversation(conversation)
    conversation_manager.display_status('success', "Name confirmed")
    conversation_manager.proceed_to_next_question(conversation_id)



def main():
    st.sidebar.title("Care Home Incident and Accident Reporting System")
    st.sidebar.image("logo.png", caption="Care Home AI Agent", width=200)
    add_custom_css()

    if st.sidebar.button("Start Conversation") and not st.session_state.get('conversation_active', False):
        start_conversation()
    if st.sidebar.button("Stop Conversation") and st.session_state.get('conversation_active', False):
        stop_conversation()

    conversation_manager = st.session_state.get('conversation_manager')
    conversation_id = st.session_state.get('conversation_id')

    if conversation_manager and conversation_id:
        conversation = conversation_manager.conversations.get(conversation_id)
        if conversation:
            if conversation.waiting_for_event_type_selection:
                if not st.session_state['selected_event_type']:
                    st.selectbox(
                        "Please select the type of event:",
                        conversation.event_type_options,
                        key='selected_event_type',
                        index=None,
                        placeholder="Please select the type of event",
                    )
                else:
                    conversation.waiting_for_event_type_selection = False
                    conversation_manager._add_message(conversation, "user", st.session_state['selected_event_type'], "answer", "Q1")
                    conversation.event_type = st.session_state['selected_event_type']
                    render_previous_conversation(conversation)
                    conversation_manager.display_status('success', "Event type confirmed")
                    reinitialize_conversation(conversation)
                return


if __name__ == "__main__":
    if 'conversation_active' not in st.session_state:
        st.session_state['conversation_active'] = False
    if 'corrected_name' not in st.session_state:
        st.session_state['corrected_name'] = ""

    main()
