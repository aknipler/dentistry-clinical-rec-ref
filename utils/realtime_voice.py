"""OpenAI Realtime speech-to-speech voice chat for roleplay stages.

The browser connects directly to OpenAI's Realtime API over WebRTC using a
short-lived ephemeral client secret minted here (server-side, using the
app's standard OpenAI API key). No external hosting provider, subprocess,
or local port is required since Streamlit itself never touches the media.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

import streamlit as st

from utils.mongodb import log_transcript

REALTIME_MODEL = "gpt-realtime"
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
# Dev-only switch: shows the live transcript panel in the widget for
# debugging. Not exposed to students - flip manually and restart the app.
SHOW_LIVE_TRANSCRIPT = False

# Voice options (OpenAI Realtime, GA): alloy, ash, ballad, coral, echo, sage,
# shimmer, verse, marin, cedar. "onyx" (used by the old TTS-based bot) isn't
# a valid Realtime voice, so the patient stage is remapped to "ash".
VOICE_STAGES = {
    "patient_interaction": {
        "prompt_path": "prompts/patient_interaction_prompt.txt",
        "transcript_collection": "patient_interaction_transcripts",
        "session_state_key": "patient_transcript_id",
        "voice": "ash",
    },
}

SESSION_KEY_STATE = "realtime_voice_state"

_FRONTEND_DIR = Path(__file__).resolve().parent / "realtime_voice_frontend"
_HTML = (_FRONTEND_DIR / "widget.html").read_text(encoding="utf-8")
_CSS = (_FRONTEND_DIR / "widget.css").read_text(encoding="utf-8")
_JS = (_FRONTEND_DIR / "widget.js").read_text(encoding="utf-8")

_realtime_voice_component = st.components.v2.component(
    name="realtime_voice",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def initialise_voice_bot_page(page_init_key: str) -> None:
    """Set up session state for a voice roleplay page on its first visit."""
    if "patient_interaction_finished" not in st.session_state:
        st.session_state.patient_interaction_finished = False
    if SESSION_KEY_STATE not in st.session_state:
        st.session_state[SESSION_KEY_STATE] = {}

    if page_init_key not in st.session_state.initialised_pages:
        st.session_state.initialised_pages.add(page_init_key)
        st.session_state.conversation_active = False
        st.session_state[SESSION_KEY_STATE].pop(page_init_key, None)
        st.session_state.handover_timer_started_at = None
        st.session_state.handover_timer_duration_seconds = 130


def _load_system_prompt(prompt_path: str) -> str:
    try:
        text = Path(prompt_path).read_text(encoding="utf-8")
    except OSError:
        text = "You are a helpful assistant taking part in a roleplay exercise."
    # return text 
    return text + " Do not describe any actions, thoughts, or movements."


def _mint_ephemeral_client_secret(client, model: str, voice: str, instructions: str) -> dict:
    """Mint a short-lived Realtime API client secret for the browser to use directly.

    Authenticates with the app's standard OpenAI API key (never sent to the
    browser), per OpenAI's recommended flow for WebRTC clients.
    """
    payload = json.dumps(
        {
            "session": {
                "type": "realtime",
                "model": model,
                "instructions": instructions,
                "audio": {
                    "output": {"voice": voice},
                    "input": {"transcription": {"model": TRANSCRIPTION_MODEL}},
                },
            },
            "expires_after": {"anchor": "created_at", "seconds": 600},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url="https://api.openai.com/v1/realtime/client_secrets",
        data=payload,
        headers={
            "Authorization": f"Bearer {client.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to create OpenAI Realtime session: {detail}") from exc


def start_voice_chat(client, stage: str) -> None:
    """Mint a fresh Realtime session for this stage and mark it active."""
    if stage not in VOICE_STAGES:
        raise ValueError(f"Unknown voice stage: {stage}. Must be one of: {', '.join(VOICE_STAGES)}")

    stage_config = VOICE_STAGES[stage]
    instructions = _load_system_prompt(stage_config["prompt_path"])
    secret = _mint_ephemeral_client_secret(client, REALTIME_MODEL, stage_config["voice"], instructions)

    st.session_state[SESSION_KEY_STATE][stage] = {
        "client_secret": secret["value"],
        "should_disconnect": False,
        "finished": False,
    }
    st.session_state.conversation_active = True


def render_voice_chat(stage: str) -> dict | None:
    """Render the voice chat widget for this stage and return its latest reported state."""
    state = st.session_state[SESSION_KEY_STATE].get(stage)
    if state is None:
        return None

    result = _realtime_voice_component(
        data={
            "client_secret": state["client_secret"],
            "should_disconnect": state["should_disconnect"],
            "show_transcript": SHOW_LIVE_TRANSCRIPT,
        },
        default={"status": "idle", "messages": []},
        on_status_change=lambda: None,
        on_messages_change=lambda: None,
        key=f"realtime_voice_{stage}",
    )
    return {"status": result.status, "messages": result.messages or []}


def request_finish_voice_chat(stage: str) -> None:
    """Ask the widget to disconnect; the transcript is saved once it reports back."""
    state = st.session_state[SESSION_KEY_STATE].get(stage)
    if state is not None:
        state["should_disconnect"] = True


def handle_voice_chat_result(stage: str, result: dict | None) -> bool:
    """Persist the transcript once the widget confirms it has disconnected.

    Returns True once the transcript has been saved and stage flags updated,
    signalling the caller should rerun.
    """
    state = st.session_state[SESSION_KEY_STATE].get(stage)
    if state is None or state.get("finished") or result is None:
        return False
    if result.get("status") != "disconnected":
        return False

    stage_config = VOICE_STAGES[stage]
    messages = result.get("messages", [])

    transcript_id = log_transcript(
        st.session_state["mongodb_uri"],
        stage,
        messages,
        stage_config["transcript_collection"],
    )

    state["finished"] = True
    st.session_state.conversation_active = False
    st.session_state[f"{stage}_chat_history"] = messages
    st.session_state[f"{stage}_finished"] = True

    st.session_state.session_id = transcript_id
    st.session_state[stage_config["session_state_key"]] = transcript_id
    return True


def finish_voice_handover(stage: str, trigger: str = "manual") -> None:
    """Back-compat shim for callers (timers) that used to end the session directly.

    ``trigger`` is accepted for API compatibility but isn't used - this just
    requests disconnect; the browser widget reports back once it has
    actually disconnected, which the next handle_voice_chat_result() call
    picks up to save the transcript and update stage flags.
    """
    request_finish_voice_chat(stage)
