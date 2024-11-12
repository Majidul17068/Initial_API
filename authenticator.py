import hmac
import streamlit as st
from services.ui_helpers import add_custom_css
import main

add_custom_css()

def check_password():
    """Returns `True` if the user has entered a correct password."""

    def password_entered():
        """Checks whether the password entered by the user is correct."""
        if st.session_state["username"] in st.secrets["passwords"] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            st.query_params.rdtaska_qaw3n = "astx5pregqw2"
            st.rerun()  # Force a rerun to update the UI immediately
        else:
            st.session_state["password_correct"] = False
            st.session_state["login_attempt"] = True

    def login_form():
        """Form with widgets to collect user information."""
        st.title("Care Home Immediate Incident and Accident Reporting System")
        st.sidebar.image("Langdalelogo.png", caption="Care Home AI Agent", width=200)
        
        # Initialize session states
        if "login_attempt" not in st.session_state:
            st.session_state["login_attempt"] = False
        if "password_correct" not in st.session_state:
            st.session_state["password_correct"] = False
            
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            submitted = st.form_submit_button("Log in")
            
            if submitted:
                password_entered()

    # Check for query parameter indicating logged-in state
    rdtaska_qaw3n = st.query_params.get('rdtaska_qaw3n', "False")
    if rdtaska_qaw3n == "astx5pregqw2":
        st.session_state["password_correct"] = True

    # If login is valid, show the main app and logout button
    if st.session_state.get("password_correct", False):
        # Add a logout button to the sidebar
        if st.sidebar.button("Log Out"):
            # Clear session state and query parameters on logout
            for key in ["password_correct", "login_attempt", "username"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.query_params.clear()
            st.rerun()
            
        main.main()  # Call the main function from main.py
        st.stop()

    # Show inputs for username and password
    login_form()
    
    # Show error message if there was a failed login attempt
    if st.session_state.get("login_attempt", False) and not st.session_state.get("password_correct", False):
        st.error("Incorrect Username or Password. Please enter the correct Username and Password.")
    
    return False

if not check_password():
    st.stop()