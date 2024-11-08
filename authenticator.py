import hmac
import streamlit as st
from services.ui_helpers import add_custom_css
import main


add_custom_css()

def check_password():
    """Returns `True` if the user has entered a correct password."""

    def login_form():
        """Form with widgets to collect user information."""
        st.title("Care Home Immediate Incident and Accident Reporting System")
        st.sidebar.image("Langdalelogo.png", caption="Care Home AI Agent", width=200)
        
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether the password entered by the user is correct."""
        if st.session_state["username"] in st.secrets["passwords"] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            # del st.session_state["username"]
            
            # Set query parameter to maintain login state across page refreshes
            st.query_params.logged_in="True"
        else:
            st.session_state["password_correct"] = False

    # Check for query parameter indicating logged-in state
    logged_in = st.query_params.get('logged_in', "False")
    if logged_in == "True":
        st.session_state["password_correct"] = True

    # If login is valid, show the main app and logout button
    if st.session_state.get("password_correct", False):
        # Add a logout button to the sidebar
        if st.sidebar.button("Log Out"):
            # Clear session state and query parameters on logout
            st.session_state["password_correct"] = False
            st.query_params.clear()  # Clear all query parameters
            
            st.rerun()
              # Refresh the page to reset state
            
        main.main()  # Call the main function from main.py
        st.stop()

    # Show inputs for username and password.
    login_form()
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("Incorrect Username or Password. Please enter the correct Username and Password.")
    return False

if not check_password():
    st.stop()
