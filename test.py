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

# Counter file to track participants
counter_file = "counter.txt"
if not os.path.exists(counter_file):
    with open(counter_file, "w") as f:
        f.write("1")

with open(counter_file, "r") as f:
    counter = int(f.read().strip())

# Ticket price by group
if counter % 2 == 1:
    ticket_price = 3.8
else:
    ticket_price = 2.8

# Image paths
background_path = "Background.png"
door_marker_path = "door_marker.png"

# --- HELPER FUNCTION ---

def compose_image(D2D_value):
    base = Image.open(background_path).convert("RGBA")
    door_marker = Image.open(door_marker_path).convert("RGBA")
    
    if D2D_value == 0:
        door_size_x, door_size_y, door_x, door_y = 600, 800, 1900, 700
    elif D2D_value == 10:
        door_size_x, door_size_y, door_x, door_y = 300, 600, 1100, 650
    elif D2D_value == 30:
        door_size_x, door_size_y, door_x, door_y = 150, 300, 550, 800
    elif D2D_value == 70:
        door_size_x, door_size_y, door_x, door_y = 50, 120, 300, 880
    else:
        door_size_x, door_size_y = 400, 600
        door_x = int(1900 - D2D_value * 20)
        door_y = int(700 - D2D_value * 2)

    draw = ImageDraw.Draw(base)
    draw.rectangle(
        [(door_x, door_y), (door_x + door_size_x, door_y + door_size_y)],
        outline="cyan", width=8
    )
    return base


# --- START PAGE ---




if st.session_state.page == 'start':
    st.title("Welcome to the Train Door Choice Experiment")

    st.markdown(f"""
Dear Participant,

Thank you for your interest in this study!

This survey is part of a research project aimed at understanding how travelers make decisions when boarding underground trains (**U-Bahn**).

---

**Please read the following information carefully before starting the survey.**

**Set-up:**

Imagine you are standing on an U-Bahn platform and would like to board the train.  
In each question, you will be shown **two alternative boarding doors**, including the following information for each option:
""")

    st.image(
        "screenshot_question.png",
        caption="Example: The door is marked with a blue rectangle",
        use_container_width=True
    )

    st.markdown(f"""

- **Walking distance to door**: This indicates how far the door is from your current position on the platform.  
  The corresponding door is highlighted with a **blue rectangle** in the image.

- **Offered discount**: This is the amount subtracted from the regular trip price of **{ticket_price} Euros** if you choose this door to board.  
  It represents an incentive for using a specific door.

- **Time until train arrival**: This shows how long it will take until the train at this door arrives.  
  If the time is shown with a "next", for example, **"10 (next)"**, this means the door is part of the **next trip** — i.e., you would ignore the upcoming train and wait for the subsequent train.

---

**What you will do:**

You will be presented with a series of these boarding choices.  
In each case, your task is to **select the door you would prefer to use**.  
There are no right or wrong answers — we are only interested in your personal preferences.

---

**Data Protection and Confidentiality:**

- Your participation is entirely voluntary, and you may withdraw at any time without consequences.
- All data will be collected anonymously and used solely for academic research purposes.
- No personal information will be recorded.
- Data storage and processing comply with the General Data Protection Regulation (**GDPR/DSGVO**).

**Contact Information:**

If you have any questions about the study, please contact **Laura Knappik** at **knappik@analytics.rwth-aachen.de**.

**Demographic Information:**

At the end of the survey, we will ask a few optional questions about your background (e.g., age group, gender, travel frequency). These help us better interpret the results and remain completely anonymous.

---

By continuing, you confirm that you have read and understood the information provided above and agree to participate under these conditions.
""")



    if st.button("Start Survey"):
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

    Remember: **Next** indicates waiting for the next trip, not taking the current one. 
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
            arrival_time_1 = f"{question['alt1_T2DR'] + question['alt1_T2DS']} min (next)"
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
            arrival_time_2 = f"{question['alt2_T2DR'] + question['alt2_T2DS']} min (next)"
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
    st.title("A Few More Questions (Optional)")
    st.write("""
    Thank you very much for your participation!

    To better understand the survey results, we would like to ask you a few additional questions.  
    Your answers are completely voluntary, anonymous, and will only be used for academic research purposes.
    """)

    # Questions
    age = st.number_input("What is your age?", min_value=18, max_value=100, step=1)

    gender = st.selectbox(
        "What is your gender?",
        ["Prefer not to say", "Female", "Male", "Diverse"]
    )

    travel_freq = st.selectbox(
        "How often have you approximately traveled by train in the last 12 months?",
        ["Prefer not to say", "None", "Daily", "Weekly", "Monthly", "Yearly"]
    )

    travel_freq_1 = st.selectbox(
        "How often have you approximately traveled by ***U-Bahn*** in the last 12 months?",
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

    if st.button("Submit Demographic Data"):
        # Save demographic data
        demographic_response = pd.DataFrame([{
            'participant_number': counter,
            'age': age,
            'gender': gender,
            'travel_frequency': travel_freq,
            'ubahn_frequency' : travel_freq_1,
            'mobility': mobility

        }])

        sheet_demo = get_gsheet().worksheet("Demographics")
        sheet_demo.append_rows(demographic_response.values.tolist(), value_input_option="USER_ENTERED")

        #increase counter
        sheet_meta = get_gsheet().worksheet("Meta")
        sheet_meta.update("A1", str(counter + 1))


        st.success("Thank you for participating in our study!")
        st.stop()
  
