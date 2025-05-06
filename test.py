import streamlit as st
import pandas as pd
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw


def get_gsheet():
    from google.oauth2.service_account import Credentials
    import gspread

    credentials_dict = dict(st.secrets["gspread"])  # convert TOML object to dict
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        credentials_dict,
        scopes=scopes
    )
    gc = gspread.authorize(credentials)
    return gc.open_by_key(credentials_dict["gsheet_key"])

# --- SETUP ---

# Initialize session state variables
if 'page' not in st.session_state:
    st.session_state.page = 'start'
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'responses' not in st.session_state:
    st.session_state.responses = {}
if 'demographic_data' not in st.session_state:
    st.session_state.demographic_data = {}


# Load predefined choice sets
design = pd.read_csv("Boarding_import.csv")

# Get participant counter from Google Sheet
sheet_meta = get_gsheet().worksheet("Meta")
counter_cell = sheet_meta.acell("A1").value
counter = int(counter_cell)


# Assign both price and travel time (TT) based on participant counter
group_id = counter % 4

if group_id in [0, 1]:
    ticket_price = 3.8
else:
    ticket_price = 2.8

if group_id in [0, 2]:
    trip_duration = 10
else:
    trip_duration = 60

# Optional: store in session state for later use
st.session_state.ticket_price = ticket_price
st.session_state.trip_duration = trip_duration


# Image paths
background_path = "Background.png"
#door_marker_path = "door_marker.png"

# --- HELPER FUNCTION ---

def compose_image(D2D_value):
    base = Image.open(background_path).convert("RGBA")
#    door_marker = Image.open(door_marker_path).convert("RGBA")
    
    if D2D_value == 0:
        door_size_x, door_size_y, door_x, door_y = 700, 1000, 1900, 600
    elif D2D_value == 10:
        door_size_x, door_size_y, door_x, door_y = 350, 600, 1050, 700
    elif D2D_value == 30:
        door_size_x, door_size_y, door_x, door_y = 120, 300, 550, 800
    elif D2D_value == 70:
        door_size_x, door_size_y, door_x, door_y = 60, 150, 290, 870
    else:
        door_size_x, door_size_y = 400, 600
        door_x = int(1900 - D2D_value * 20)
        door_y = int(700 - D2D_value * 2)

    draw = ImageDraw.Draw(base)
    draw.rectangle(
        [(door_x, door_y), (door_x + door_size_x, door_y + door_size_y)],
        outline="yellow", width=8
    )
    return base


# --- START PAGE ---




if st.session_state.page == 'start':
    st.title("Welcome to the Train Door Choice Experiment")

    st.markdown(f"""
Dear Participant,

Thank you for your interest in this study!

This survey is part of a research project investigating how travelers make decisions when boarding public transport vehicles (**subway**).

---

**Please read the following information carefully before starting the survey.**

**Set-up:**

Imagine you are standing on a subway platform, about to decide where to wait for an arriving train.
You haven’t positioned yourself yet and must now choose a spot on the platform.
You are traveling alone with a small backpack on your shoulders. 

In each question, you will be shown two alternative boarding doors. Each door may belong to either the upcoming train, or the following train (i.e., you would skip the upcoming one and wait for the train after).
Each option will include the following information:
""")

    st.image(
        "screenshot_question.png",
        caption="Example: The door is marked with a yellow rectangle",
        width=600
    )

    st.markdown(f"""

Note about the image:

The train is shown only to help visualize the door locations.
In reality, no train has arrived yet — you are choosing where to position yourself before any train arrives.

- **Ticket price** Your regular ticket costs **{ticket_price} Euros**. This remains constant throughout the experiment.

- **Trip duration** Your trip from origin to destination takes **{trip_duration} minutes**. This also remains unchanged. 

- **Walking distance to door**: The distance from your current spot to the respective door. The selected door is marked with a **yellow rectangle** in the image.

- **Offered discount**: A reduction from the regular ticket price if you board through this door. For example, a discount of 1 Euro means you would pay {ticket_price}-1 Euros.

- **Time until train arrival**: This shows how long it will take until the train at this door arrives.
If the label says just a number, e.g., “10”, it means the door belongs to the upcoming train.
If the label says “10 (following train)”, it means the door belongs to the train after the upcoming one — so you would skip the first train and board the following one.""")

    st.image(
            "Display_Description.png",
            caption="Example: Upcoming and following train",
            use_container_width=True
    )
    st.markdown(f"""



 
---

**What you will do:**

You will see 12 of these door choice questions.

In each case, your task is to choose the door you would prefer to board through.
If neither option suits you, you may choose to opt out.

There are no right or wrong answers — we are interested in your personal preferences.

---

**Demographic Information:**

At the end of the survey, we will ask a few optional questions about your background (e.g., age group, gender, travel frequency). These help us better interpret the results and remain completely anonymous.

**Data Protection and Confidentiality:**

- Your participation is entirely voluntary, and you may withdraw at any time without consequences.
- All data will be collected anonymously and used solely for academic research purposes.
- No personal information will be recorded.
- Data storage and processing comply with the General Data Protection Regulation (**GDPR/DSGVO**).

**Contact Information:**

If you have any questions about the study, please contact **Laura Knappik** at **knappik@analytics.rwth-aachen.de**.


---

By continuing, you confirm that you have read and understood the information provided above and agree to participate under these conditions.
""")

    # --- COMPREHENSION CHECK ---

    # --- COMPREHENSION CHECK ---
    st.markdown("### Quick Check Before Starting")
    st.markdown("""
    To make sure you have read and understood the key information, please answer the following short questions in order to proceed:
    """)

    with st.form("comprehension_form"):
        price_options = [
            f"€{ticket_price - 2:.2f}",
            f"€{ticket_price - 1:.2f}",
            f"€{ticket_price:.2f}",  # correct
            f"€{ticket_price + 1:.2f}"
        ]
        answer_price = st.radio(
            "1. What is the regular ticket price for your trip in this experiment?",
            options=price_options,
            key="comprehension_price"
        )
    
        duration_options = [
            f"{trip_duration - 50} minutes" if trip_duration == 60 else "5 minutes",
            f"{trip_duration - 1} minutes",
            f"{trip_duration} minutes",
            f"{trip_duration + 10} minutes"
        ]
        answer_duration = st.radio(
            "2. How long is your trip from origin to destination?",
            options=duration_options,
            key="comprehension_duration"
        )
    
        travel_options = [
            "With friends and luggage",
            "Alone with a suitcase",
            "Alone with a small backpack",  # correct
            "In a group with bikes"
        ]
        answer_alone = st.radio(
            "3. How are you traveling in this experiment?",
            options=travel_options,
            key="comprehension_alone"
        )
    
        confirm_clicked = st.form_submit_button("Confirm Answers")
    
    if confirm_clicked:
        is_correct_price = answer_price == f"€{ticket_price:.2f}"
        is_correct_duration = answer_duration == f"{trip_duration} minutes"
        is_correct_alone = answer_alone == "Alone with a small backpack"
    
        if is_correct_price and is_correct_duration and is_correct_alone:
            st.success("All correct – you may now proceed to the survey.")
            st.session_state.allow_start = True
        else:
            st.error("One or more answers are incorrect. Please read the instructions above again carefully.")
            st.session_state.allow_start = False

    
    # --- Conditional start button ---
    if st.session_state.get("allow_start", False) and st.button("Start Survey"):
        st.session_state.page = 'survey'
        st.session_state.current_idx = 0  # reset index
        st.rerun()


# --- SURVEY PAGE ---

elif st.session_state.page == 'survey':
    st.title("Train Door Choice Survey")
    
    st.write(f"""
    Imagine you are traveling alone, carrying only a small backpack.

    Remember: The regular ticket price for this trip is **{ticket_price} Euros**.  
    Each door option may offer a discount that will reduce this price.

    Remember: The total travel time for your trip is **{trip_duration}** minutes. 

    Remember: **Following train** indicates waiting for the next trip, not taking the current one. 
    """)

    
    questions = design.copy().reset_index(drop=True)

    total_questions = len(questions)

    idx = st.session_state.current_idx
    if f"temp_choice_{idx}" not in st.session_state:
        st.session_state[f"temp_choice_{idx}"] = st.session_state.responses.get(idx, "Door A")

    question = questions.iloc[idx]

    st.markdown(f"### Choice Set {idx+1} of {total_questions}")

    # Create images
    image_A = compose_image(question['alt1_D2D'])
    image_B = compose_image(question['alt2_D2D'])


    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Door A")
        st.image(image_A, caption="Option A", use_container_width=True)
        st.markdown(f"**Walking distance to door**: {question['alt1_D2D']} m")
        discount_amount_1 = round(ticket_price * question['alt1_D'] / 100, 2)
        st.markdown(f"**Offered discount**: {question['alt1_D']} % (−{discount_amount_1} €)")
        if question['alt1_TS'] == 1:
            arrival_time_1 = f"{question['alt1_T2DR'] + question['alt1_T2DS']} min (following train)"
        else:
            arrival_time_1 = f"{question['alt1_T2DR']} min"

        st.markdown(f"**Time until train arrival**: {arrival_time_1}")



    with col2:
        st.subheader("Door B")
        st.image(image_B, caption="Option B", use_container_width=True)
        st.markdown(f"**Walking distance to door**: {question['alt2_D2D']} m")
        discount_amount_2 = round(ticket_price * question['alt2_D'] / 100, 2)
        st.markdown(f"**Offered discount**: {question['alt2_D']} % (−{discount_amount_2} €)")
        if question['alt2_TS'] == 1:
            arrival_time_2 = f"{question['alt2_T2DR'] + question['alt2_T2DS']} min (following train)"
        else:
            arrival_time_2 = f"{question['alt2_T2DR']} min"

        st.markdown(f"**Time until train arrival**: {arrival_time_2}")
    



    # Get participant's choice
    with st.form(key=f"form_{idx}"):
        st.session_state[f"temp_choice_{idx}"] = st.radio(
            "Which option do you choose?",
            ("Door A", "Door B", "None of both"),
            index=("Door A", "Door B", "None of both").index(
                st.session_state[f"temp_choice_{idx}"]
            )
        )
    
        col_back, col_next = st.columns([1, 5])
        with col_back:
            back_clicked = st.form_submit_button("Back")
        with col_next:
            next_clicked = st.form_submit_button("Next" if idx < total_questions - 1 else "Submit Survey")
    
        if back_clicked and idx > 0:
            st.session_state.current_idx -= 1
            st.rerun()
    
        if next_clicked:
            st.session_state.responses[idx] = st.session_state[f"temp_choice_{idx}"]
    
            if idx < total_questions - 1:
                st.session_state.current_idx += 1
                st.rerun()
            else:
                # Create DataFrame from responses
                df_responses = pd.DataFrame([
                    {
                        'participant_number': counter,
                        'ticket_price': st.session_state.ticket_price,
                        'trip_duration': st.session_state.trip_duration,
                        'choice_set': i + 1,
                        'choice': st.session_state.responses[i],
                        'alt1_D': questions.iloc[i]['alt1_D'],
                        'alt1_D2D': questions.iloc[i]['alt1_D2D'],
                        'alt1_TS': questions.iloc[i]['alt1_TS'],
                        'alt1_T2DR': questions.iloc[i]['alt1_T2DR'],
                        'alt1_T2DS': questions.iloc[i]['alt1_T2DS'],
                        'alt2_D': questions.iloc[i]['alt2_D'],
                        'alt2_D2D': questions.iloc[i]['alt2_D2D'],
                        'alt2_TS': questions.iloc[i]['alt2_TS'],
                        'alt2_T2DR': questions.iloc[i]['alt2_T2DR'],
                        'alt2_T2DS': questions.iloc[i]['alt2_T2DS']
                    }
                    for i in range(total_questions)
                ])
    
                sheet_responses = get_gsheet().worksheet("Responses")
                sheet_responses.append_rows(df_responses.values.tolist(), value_input_option="USER_ENTERED")
    
                st.session_state.page = 'demographics'
                st.rerun()


elif st.session_state.page == 'demographics':
    st.title("A Few More Questions")
    st.write("""
    Thank you very much for your participation!

    To better understand the survey results, we would like to ask you a few additional questions.  
    Your answers are completely voluntary, anonymous, and will only be used for academic research purposes.
    """)

    with st.form("demographics_form"):
        age = st.selectbox(
            "What is your age group?",
            ["Prefer not to say", "18–29", "30–39", "40–49", "50–59", "60–69", "70+"]
        )


        gender = st.selectbox(
            "What is your gender?",
            ["Prefer not to say", "Female", "Male", "Diverse"]
        )

        travel_freq = st.selectbox(
            "How often have you approximately traveled by train in the last 12 months?",
            ["Prefer not to say", "None", "Daily", "Weekly", "Monthly", "Yearly"]
        )

        travel_freq_1 = st.selectbox(
            "How often have you approximately traveled by ***subway*** in the last 12 months?",
            ["Prefer not to say", "None", "Daily", "Weekly", "Monthly", "Yearly"]
        )

        mobility = st.select_slider(
            "How would you assess your mobility?",
            options=[
                "Prefer not to say",
                "0 - No problems",
                "1 - Minor limitations",
                "2 - Moderate limitations",
                "3 - Severe limitations",
                "4 - Unstable / Handicapped"
            ]
        )

        # Make sure this is at the same level as the other inputs
        submitted = st.form_submit_button("Submit Demographic Data")

    if submitted and not st.session_state.get("submitted_demo", False):
    # Save demographic data
        demographic_response = pd.DataFrame([{
            'participant_number': counter,
            'age': age,
            'gender': gender,
            'travel_frequency': travel_freq,
            'ubahn_frequency': travel_freq_1,
            'mobility': mobility
        }])
    
        sheet_demo = get_gsheet().worksheet("Demographics")
        sheet_demo.append_rows(demographic_response.values.tolist(), value_input_option="USER_ENTERED")
    
        sheet_meta.update("A1", [[str(counter + 1)]])
        
        st.session_state.submitted_demo = True  # ✅ prevent further submissions
    
        st.session_state.page = 'end'
        st.rerun()

elif st.session_state.page == 'end':
    st.title("Thank You for Your Participation!")

    st.markdown("""
    Your responses have been recorded successfully.

    If you have any questions or would like to know more about this research, feel free to contact:

    Laura Knappik
    RWTH Aachen University  
    knappik@analytics.rwth-aachen.de

    ---

    You may now close this tab or window.

    """)

        

