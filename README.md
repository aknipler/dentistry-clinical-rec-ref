# Dentistry Clinical Recommendation & Referral Bot

A Streamlit teaching activity for dental students. Students play a clinician
who must interview a simulated patient about a clinical recommendation, then
receive AI-generated written feedback on their performance.

The activity has three linear stages, each its own Streamlit page:

1. **Case Information** — the student reviews a patient chart and clinical recommendation.
2. **Patient Interaction** — the student interviews a simulated patient
   (voice conversation) to discuss a clinical recommendation and address
   their concerns.
3. **Feedback** — the transcript is reviewed by AI and produces a structured,
   educational written report (summary, communication under pressure,
   strengths/improvements, clinical safety notes).

Students can only reach a stage once the previous one is marked finished
(`patient_interaction_finished` in session state), and every transcript is
stored in MongoDB keyed by the student's anonymous identifier so it can be reviewed
later.


## Project structure

```
Home.py                              # Landing page: identifier entry, session_state setup()
pages/
├── 1_1._Case_Information.py         # Stage 1: case information review
├── 2_2._Patient_Interaction.py      # Stage 2: voice bot, patient interview
└── 3_3._Feedback.py                 # Stage 3: AI-generated written feedback
utils/
├── realtime_voice.py                # Mints OpenAI Realtime ephemeral keys, renders the voice widget, saves transcripts
├── realtime_voice_frontend/         # HTML/CSS/JS for the Streamlit v2 custom component (WebRTC to OpenAI)
├── streamlit_utils.py               # Shared UI helpers (timer panel, patient chart display)
└── mongodb.py                       # Transcript + identifier persistence
prompts/
├── patient_interaction_prompt.txt   # Patient roleplay system prompt
├── patient_medical_history.txt      # Patient chart shown to the student
└── feedback_prompt.txt              # Feedback report structure/instructions
scripts/
├── generate_and_load_identifiers.py # Create + upload student identifiers
├── load_identifiers.py              # Upload an existing identifier CSV
└── create_index.py                  # MongoDB index setup
```

## Setup

### 1. Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Requires Python with access to a microphone-capable browser for testing. The
student's browser connects directly to OpenAI's Realtime API over WebRTC
(see Secrets below) - Streamlit never touches the audio itself, so there's no
separate process or port to expose, on Streamlit Community Cloud or locally.

### 2. Secrets

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your_openai_api_key"
MONGODB_CONNECTION_STRING = "your_mongodb_connection_string"
MONGODB_DATABASE_NAME = "your_database_name"
```

- **OpenAI** powers the feedback and the voice bots end-to-end via the Realtime API
  (speech-to-speech): the student's browser connects directly to OpenAI over
  WebRTC using a short-lived ephemeral key minted server-side from this key.
- **MongoDB** stores valid student identifiers and every stage's transcript.

### 3. Student identifiers

Create a CSV with student information (e.g. `students.csv`):

```csv
order_id,
0,
1,
2,
```

Generate identifiers and load them into MongoDB:

```powershell
python scripts/generate_and_load_identifiers.py
```

Gives:

```csv
order_id, unique_id
0, EXAMPLE-DLVNEI
1, EXAMPLE-ABC123
2, EXAMPLE-XYZ789
```

This creates unique identifiers, saves a mapping CSV locally 
and uploads only the identifiers themselves to the `valid_identifiers`
collection in MongoDB.

### 4. Running the app

```powershell
streamlit run Home.py
```

Open the app, enter a valid identifier on the Home page, then proceed through
the three stages in order.

## Troubleshooting

- **Transcript not saving / can't progress to the next stage** — the
  transcript is saved directly by Streamlit once the voice widget reports
  that it has disconnected (see `handle_voice_chat_result()` in
  `utils/realtime_voice.py`); check for MongoDB connection errors in the app
  logs.
- **Feedback looks truncated** — check for a "cut off because it reached the
  model's token limit" warning on the Feedback page; increase
  `FEEDBACK_MAX_TOKENS` in `pages/3_3._Feedback_-_GPT.py` if needed.

## Security considerations

- Never commit `.env`, `.streamlit/secrets.toml`, or any CSV containing
  student-identifier mappings.
- Only opaque identifiers (no personal information) are stored in MongoDB.
- Regular database backups are recommended.
