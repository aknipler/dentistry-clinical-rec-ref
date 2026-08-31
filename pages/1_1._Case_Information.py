
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
st.markdown("""

You are a student clinician working in the Melbourne Dental Clinic. You are seeing Daniel, a 31-year-old new patient, for a comprehensive oral health assessment.
Before the appointment, you reviewed the available clinical information with your clinical supervisor. Your supervisor advised that a new set of bitewing radiographs is likely to be indicated as part of Daniel’s comprehensive assessment.
Begin the consultation by introducing yourself and taking Daniel's medical, dental and social history.
Communicate with Daniel as you would with a patient in clinical practice.
""")
# Create Computer display
computer_screen_display("patient_medical_history")


