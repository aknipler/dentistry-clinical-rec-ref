import streamlit as st
from utils.mongodb import check_identifier
from utils.streamlit_utils import initialise_streamlit_session_state
from openai import OpenAI

def is_identifier_valid():
    identifier = st.session_state.get("user_identifier", "").strip()
    if not identifier:
        return False
    return check_identifier(st.session_state["mongodb_uri"], identifier)

def setup():

    # Initialize Streamlit session state variables (there are a lot!)
    initialise_streamlit_session_state()

    # Set up OpenAI API client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    return client

def init_page():
    setup()
    
    st.title("Patient Recommendation Conversation")
    st.markdown(
    """
You are a student clinician working in the Dental Teaching Clinic.

You are seeing a new patient at Melbourne Dental Clinic. During the clinical
 examination, several large carious lesions have been identified.

You are concerned that there may also be decay between the teeth that cannot 
 be seen clearly during the clinical examination. You are recommending 
 bitewing radiographs to help assess the extent and depth of the decay before 
 deciding on the most appropriate treatment plan.

The patient is concerned about radiation exposure and does not want radiographs 
 taken today. The patient suggests that if there is a cavity, you should “just 
 drill it” and fix it.

During this appointment, your role is to discuss the recommendation with the 
 patient, explore their concerns, explain the reason for the radiographs in 
 language the patient can understand, and support the patient to make an 
 informed decision.

The consultation is taking place within a standard new-patient appointment. You 
 should communicate clearly, professionally and at a pace that allows the patient 
 to understand the information and participate in the discussion.

You should not pressure the patient to accept radiographs. If the patient 
 continues to refuse, your role is to ensure they understand the possible risks 
 and limitations of proceeding without radiographic information and
 to consider appropriate next steps. This may include discussing the case with a 
 supervisor, delaying treatment planning, arranging follow-up, clinical 
 monitoring, documenting the discussion, or providing safety-netting advice. \n
    
**Disclaimer: This is experimental and may not work perfectly, so apply your 
 clinical judgement and common sense to the interactions and feedback. If you 
 have any questions or concerns, please contact your supervisor.**
    """
    )


    st.markdown(
    """
    ## Your Task
    -	Review the available patient case information.
    -	Conduct a patient interview to gather any additional information required.
    -	Review the feedback on the session.
    """
    )
    
    st.markdown(
    """
    ## Success Criteria

    You will receive feedback assessed on your ability to:
    - communicate effectively with the patient
    - explore the patient’s concerns about radiographs
    - address misinformation respectfully
    - explain the purpose of bitewing radiographs using language the patient can understand
    - explain the possible risks and limitations of proceeding without radiographs
    - check the patient’s understanding
    - support informed decision-making
    - respect the patient’s autonomy
    - avoid pressured consent
    - recognise when supervisor input may be appropriate
    - communicate professionally within a challenging consultation
    """)
    st.markdown(
        "## Instructions\n"
        "1. Enter your unique identifier below. This will be used to associate your conversation records with you.\n"
        "2. In the Case Information tab, assess the patients medical history. \n"
        "3. In the Patient Conversation tab, conduct a patient assessment. Only when you are finished the conversation click the `finish` button. You will not be able to undo this submission.\n"
        "4. In the Feedback tab, review your performance. If you have any additional questions about your feedback or performance, please contact your supervisor.\n"
        "\n**Note: Please ensure you have a stable internet connection, a quiet environment and a suitable microphone to prevent any issues from occurring.**"
    )

    # Add identifier input after welcome message
    identifier = st.text_input(
        "Please enter your unique identifier:",
        key="identifier_input",
        value=st.session_state.get("user_identifier", ""),
        help="This identifier will be stored with your conversation records"
    )

    if identifier:
        if check_identifier(st.session_state["mongodb_uri"], identifier):
            st.session_state["user_identifier"] = identifier
            st.success("✅ Identifier validated successfully. You can now proceed to the Case Information page.")
        else:
            st.error("❌ Invalid identifier. Please enter a valid identifier.")
            st.session_state["user_identifier"] = ""
    else:
        st.warning("⚠️ Please enter your identifier before starting any conversations.")

if __name__ == "__main__":
    init_page()
