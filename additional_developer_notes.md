
## How the voice bot works

The patient conversation is real-time voice, not text chat. Streamlit itself
can't reach the microphone, so the student's browser connects **directly to
OpenAI's Realtime API** over WebRTC
(`utils/realtime_voice_frontend/`, mounted as a Streamlit
[custom component v2](https://docs.streamlit.io/develop/concepts/custom-components/components-v2)
via `utils/realtime_voice.py`) — there's no separate bot process, external
hosting provider, or port to expose. OpenAI's `gpt-realtime` model handles
speech-to-text, the conversation itself, and text-to-speech in one hop.

`utils/realtime_voice.py` is stage-agnostic (keyed by a `stage` string), even
though only the `patient_interaction` stage is currently used - which prompt
to load, which Mongo collection to save into, and which voice to use are
configured per stage in `VOICE_STAGES` in that file. Before each conversation
starts, Streamlit mints a short-lived ephemeral client secret server-side
(using the app's `OPENAI_API_KEY`, which never reaches the browser) via
`POST /v1/realtime/client_secrets`; the browser then uses that ephemeral key
to open the WebRTC connection directly with OpenAI.

Because the browser (not Streamlit) holds the live connection, ending a
conversation is a two-step, reactive process: clicking **Finish Conversation**
just asks the widget to disconnect (`request_finish_voice_chat()`); once the
widget's JavaScript actually tears down the `RTCPeerConnection` and reports
back a `"disconnected"` status (which triggers its own Streamlit rerun),
`handle_voice_chat_result()` saves the transcript directly to MongoDB via
`log_transcript()` — no subprocess, hangup route, or transcript polling is
needed.
