import streamlit as st
from datetime import datetime, timezone

from Home import setup
from utils.realtime_voice import (
    start_voice_chat,
    render_voice_chat,
    request_finish_voice_chat,
    handle_voice_chat_result,
    initialise_voice_bot_page,
)
from utils.streamlit_utils import enforce_max_duration

# The student's browser connects directly to OpenAI's Realtime API over
# WebRTC (never to this container) to reach the microphone. This page only
# mints a short-lived ephemeral key and renders the widget that manages that
# connection.

PATIENT_INTERACTION_MAX_SECONDS = 8 * 60

client = setup()

PAGE_INIT_KEY = "patient_interaction"
initialise_voice_bot_page(PAGE_INIT_KEY)


if not bool(st.session_state.get("user_identifier", "").strip()):
    st.error("Please enter your identifier on the Home page before starting the conversation.")
    st.stop()
elif st.session_state.patient_interaction_finished:
    st.success("Patient interaction completed, proceed to Feedback page.")
    st.stop()


# --- Start ---
st.title("Patient Interaction")

if st.button("Restart Voice Chat" if st.session_state.conversation_active else "Start Voice Chat"):
    try:
        start_voice_chat(client, stage="patient_interaction")
        st.session_state.patient_interaction_started_at_utc = datetime.now(timezone.utc)
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))
        st.session_state.conversation_active = False


st.markdown(
    "Note: This conversation has a max time limit of 8 minutes. When you click **Start Voice Chat** the conversation will begin. Using your "
    "microphone, conduct your interview with the patient. Click **Finish Conversation** when done."
)

# --- Embedded voice client ---
if st.session_state.conversation_active:
    result = render_voice_chat("patient_interaction")
    st.caption(
        "Click **Connect microphone** below and allow microphone access when prompted, then just speak. "
        "The timer started when you pressed Start Voice Chat."
    )
    if handle_voice_chat_result("patient_interaction", result):
        st.rerun()


# Silent 8-minute cap to prevent excessive usage - no countdown is shown to
# the student (unlike the timer panel above), it just ends the conversation
# once the limit is hit.
enforce_max_duration(
    "patient_interaction",
    st.session_state.get("patient_interaction_started_at_utc"),
    PATIENT_INTERACTION_MAX_SECONDS,
)


# --- Finish ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if not st.session_state.patient_interaction_finished and st.session_state.conversation_active:
        if st.button("Finish Conversation", key="finish_patient_interaction", use_container_width=True):
            request_finish_voice_chat("patient_interaction")
            st.rerun()

if st.session_state.patient_interaction_finished:
    st.success("Patient interaction completed, proceed to Feedback page.")

