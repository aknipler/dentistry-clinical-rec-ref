
import streamlit as st
import time
from datetime import datetime, timezone

from Home import setup
from utils.mongodb import get_latest_transcript_since
from utils.streamlit_utils import render_timer_panel, computer_screen_display, enforce_max_duration


# --- Start ---

if not bool(st.session_state.get("user_identifier", "").strip()):
    st.error("Please enter your identifier on the Home page before starting the conversation.")
    st.stop()

st.title("Case Information")

# Create Computer display
computer_screen_display("patient_medical_history")


