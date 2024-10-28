import hmac
import streamlit as st
from services.ui_helpers import add_custom_css
import main



add_custom_css()

def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        st.title("Care Home Incident and Accident Reporting System")
        st.sidebar.image("Langdalelogo.png", caption="Care Home AI Agent", width=200)
        
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        main.main()  # Call the main function from main.py
        st.stop() 
        

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("Incorrect Username or Pasword. Please enter correct Username and Password.")
    return False


if not check_password():
    st.stop()

check_password()
