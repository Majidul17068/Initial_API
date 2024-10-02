import streamlit as st

def add_custom_css():
    st.markdown(
        """
        <style>
        .user-message, .bot-message {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        .bot-message {
            justify-content: flex-start;
        }
        .user-message {
            justify-content: flex-end;
        }
        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin: 0 10px;
        }
        .message-text {
            background-color: #f1f0f0;
            padding: 10px;
            color: #000;
            border-radius: 10px;
            max-width: 70%;
        }
        .user-message .message-text {
            background-color: #daf0da;
        }
        </style>
        """, unsafe_allow_html=True
    )

def display_chat_message(is_user, message_text):
    avatar_bot = "https://www.w3schools.com/howto/img_avatar.png"
    avatar_user = "https://www.w3schools.com/howto/img_avatar2.png"

    if is_user:
        st.markdown(f"""
        <div class="user-message">
            <div class="message-text">{message_text}</div>
            <img src="{avatar_user}" alt="User Avatar" class="avatar">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="bot-message">
            <img src="{avatar_bot}" alt="Bot Avatar" class="avatar">
            <div class="message-text">{message_text}</div>
        </div>
        """, unsafe_allow_html=True)

