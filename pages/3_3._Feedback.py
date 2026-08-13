import streamlit as st
from Home import setup
from pathlib import Path
from utils.mongodb import log_transcript, get_transcript
from openai import OpenAI


if not bool(st.session_state.get("user_identifier", "").strip()):
    st.error("Please enter your identifier on the Home page before starting the conversation.")
    st.stop()
elif not st.session_state.patient_interaction_finished:
    st.error("Please complete the Patient Interaction first.")
    st.stop()


MAXIMUM_RESPONSES = 1000

client = setup()

avatar_image_path = " "
TRANSPARENT_AVATAR = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# st.session_state.feedback_chat_history = None
if st.session_state.feedback_chat_history is None or len(st.session_state.feedback_chat_history) == 0:
    st.title("Generating feedback...")

    with st.chat_message("assistant", avatar=TRANSPARENT_AVATAR):
        initial_prompt = st.session_state["feedback_prompt"]
        patient_transcript_id = (
            st.session_state.get("patient_transcript_id")
            or st.session_state.get("session_id")
        )

        if not patient_transcript_id:
            st.error("Missing transcript references. Please complete Patient Interaction first.")
            st.stop()

        patient_interaction_transcript = get_transcript(
            st.session_state["mongodb_uri"],
            st.session_state["mongodb_database_name"],
            "patient_interaction_transcripts",
            patient_transcript_id,
        )

        FEEDBACK_MAX_TOKENS = 6144

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": initial_prompt},
                {"role": "user", "content": "patient interaction transcript: " + str(patient_interaction_transcript)},
            ],
            max_completion_tokens=FEEDBACK_MAX_TOKENS
        )

        if response.choices[0].finish_reason == "max_tokens":
            st.warning(
                "The feedback response was cut off because it reached the model's "
                "token limit. Consider increasing FEEDBACK_MAX_TOKENS further."
            )

        # for block in response.choices[0].message:
        #     if block.type == "text":
        st.session_state.feedback_chat_history = response.choices[0].message.content

                # Use a dedicated key rather than the shared "session_id" -
                # patient_transcript_id above falls back to session_id, so
                # overwriting it here would break that fallback if this page
                # reruns before that key is read again.
        st.session_state.feedback_transcript_id = log_transcript(
            st.session_state["mongodb_uri"],
            "feedback",
            st.session_state.feedback_chat_history,
            "feedback_transcripts"
        )

    # Only rerun once, now that generation is done, so the page redraws showing
    # the saved feedback via the branch below instead of regenerating again.
    st.rerun()
else:
    st.markdown(st.session_state.feedback_chat_history)