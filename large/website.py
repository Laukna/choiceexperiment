import streamlit as st
import pandas as pd
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw

# Base directory for relative assets (folder containing this script)
BASE_DIR = os.path.dirname(__file__)


@st.cache_resource
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


@st.cache_data
def load_design():
    csv_path = os.path.join(BASE_DIR, "choice_sets_large.csv")
    return pd.read_csv(csv_path)

design = load_design()


# Get participant counter from Google Sheet
if 'counter' not in st.session_state:
    sheet_meta = get_gsheet().worksheet("Meta")
    counter_cell = sheet_meta.acell("A1").value
    st.session_state.counter = int(counter_cell)

counter = st.session_state.counter

#Split choice sets into two groups 
if 'cs_group' not in st.session_state:
    st.session_state.cs_group = 'A' if counter % 2 == 1 else 'B'

cs_group = st.session_state.cs_group

# Check Boarding.csv -> column called CS?
if cs_group == 'A':
    design = design[design['CS'].between(1, 12)].sort_values("CS").copy()
else:
    design = design[design['CS'].between(13, 24)].sort_values("CS").copy()

# Assign trip attributes based on participant counter
@st.cache_data
def load_scenarios():
    trip_durations = [10, 60]
    ticket_prices = [2.3, 3.8]
    previous_transfers = ["yes_no_change", "yes_with_change", "no"]
    time_recent_options = [1, 2, 4]
    time_subseq_options = [5, 10]
    travel_mode = ["alone_backpack", "alone_business", "group_luggage"] 

    rows = []
    scenario_id = 1
    for td in trip_durations:
        for tp in ticket_prices:
            for pt in previous_transfers:
                for tr in time_recent_options:
                    for ts in time_subseq_options:
                        for tm in travel_mode:
                            rows.append(
                                {
                                    "scenario_id": scenario_id,
                                    "trip_duration": td,
                                    "ticket_price": tp,
                                    "previous_transfers": pt,
                                    "time_recent": tr,
                                    "time_subseq": ts,
                                    "travel_mode": tm
                                }
                            )
                            scenario_id += 1

    return pd.DataFrame(rows)

scenarios = load_scenarios()
n_scenarios = len(scenarios)

# Zuweisung: rotiert deterministisch durch alle 72 Szenarien
scenario_idx = (counter - 1) % n_scenarios
scenario = scenarios.iloc[scenario_idx]

# In Session State speichern: bleibt für alle Choice Sets dieses Teilnehmenden gleich
st.session_state.scenario_id = int(scenario["scenario_id"])
st.session_state.trip_duration = int(scenario["trip_duration"])
st.session_state.ticket_price = float(scenario["ticket_price"])
st.session_state.previous_transfers = scenario["previous_transfers"]
st.session_state.time_recent = int(scenario["time_recent"])
st.session_state.time_subseq = int(scenario["time_subseq"])
st.session_state.travel_mode = scenario["travel_mode"]

ticket_price = st.session_state.ticket_price
trip_duration = st.session_state.trip_duration
previous_transfers = st.session_state.previous_transfers
time_recent = st.session_state.time_recent
time_subseq = st.session_state.time_subseq
travel_mode = st.session_state.travel_mode

if previous_transfers == "yes_with_change":
    pt_text = "You had previous transfers and accepted changing your boarding door to receive the discount."
elif previous_transfers == "no":
    pt_text = "You did not have previous transfers; this is your first boarding for the trip."
else:
    pt_text = "You had previous transfers but did not change your boarding door to receive the discount."

if travel_mode == "alone_backpack":
    tm_text = "You are traveling alone with a small backpack."
elif travel_mode == "alone_business":
    tm_text = "You are traveling alone with a business bag. You have an important meeting to attend."
else:
    tm_text = "You are traveling in a group of 6 persons and carrying luggage."

# # Image paths
# background_path = "Background.png"
# #door_marker_path = "door_marker.png"

# # --- HELPER FUNCTION ---
# def load_pre_rendered_image(D2D_value):
#     path = f"door_images/door_d2d_{D2D_value}.png"
#     return Image.open(path)

# --- START PAGE ---

if st.session_state.page == 'start':
    st.title("Welcome to the Train Door Choice Experiment")

    st.markdown(f"""
Dear Participant,

Thank you very much for your interest in this study.
This survey is part of a research project examining how travelers choose where to board public transport vehicles (**subways**).

---

**Before you start:**
Please read this short explanation carefully.
It contains all the information needed to understand the task. 

**Your situation in this experiment:**
Imagine you are standing on a subway platform and have not yet chosen where to wait for the train.
Throughout the entire experiment, the following conditions remain the same:
- {tm_text}
- Your regular ticket price for this trip is **{ticket_price} Euros**.
- The total travel time for your trip is **{trip_duration} minutes**.
- {pt_text}

**What you will do:**
You will answer 12 questions. In each question you will see two door options. 
Your task is to choose the door you would prefer to board through. If neither door is suitable you may select "None of both". 
There are no right or wrong answers, we are interested in you personal preferences. 

**Understanding the door information:** 
In each question, you will see two doors to choose from: Door A and Door B.
Each door is shown with a picture and several pieces of information.

The picture shows a train on the platform. In the given scenario, the train has not yet arrived and you are choosing your waiting position. The shown train only helps you see where the door is located.  


For each door, you will see the following details:
- **Walking distance to exit**: How far this door is from the nearest exit at your destination station.
- **Walking distance to door**: How far you must walk on the platform to reach this door.
- **Obstacle**: Whether something blocks your way (for example, a suitcase).
- **Crowding level at door**: How many people are already waiting at this door location.
- **Crowding level at platform**: How crowded it is on the way to the door location.
- **In-vehicle crowding**: How crowded the train is expected to be inside this door. This may be shown as colors (green = low, yellow = medium, red = high) and may appear as LED lights on the ground or on the display above the platform. 
- **Time until train arrival**: How long it will take until the train arrives. If the door belongs to the following train, this means you would skip the upcoming train and wait for the next one.
- **Offered discount**: A reduction from the regular ticket price when boarding through this door. For example, your regular ticket fare is {ticket_price} Euro and a discount of 1 Euro is applied, the final price you pay is {ticket_price - 1:.2f} Euros.

You should use all of this information to decide which door you prefer.

**Examples of what you will see:** """)
example_fig_path = os.path.join(BASE_DIR, "rectangle_exp.png")
st.image(
    example_fig_path,
    caption="Example: The door is marked with a yellow rectangle.",
    width="content"
)

crowding_real_fig_path = os.path.join(BASE_DIR, "crowding_real.png")
st.image(
    crowding_real_fig_path,
    caption="Real-world: In-vehicle crowding information shown via LED and display. ",
    width="content"
)

crowding_LED_fig_path = os.path.join(BASE_DIR, "LED_exp.png")
st.image(
    crowding_LED_fig_path,
    caption="Example: In-vehicle crowding information shown via LED. ",
    width="content"
)

crowding_display_fig_path = os.path.join(BASE_DIR, "Display_exp.png")
st.image(
    crowding_display_fig_path,
    caption="Example: In-vehicle crowding information shown via display. ",
    width="content"
)

time_fig_path = os.path.join(BASE_DIR, "Display_Description.png")
st.image(
    time_fig_path,
    caption="Real-world: Display showing upcoming and following train. ",
    width="content"
)

disc_fig_path = os.path.join(BASE_DIR, "discount.png")
st.image(
    disc_fig_path,
    caption="Example: How a discount is shown.",
    width="content"
)





st.markdown(f"""

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

    tm_options = [
            "Alone with a small backpack",
            "Alone with a business bag",
            "In a group with luggage"
        ]

    # Korrektes Label anhand des Session-States bestimmen
    travel_mode = st.session_state.travel_mode
    if travel_mode == "alone_backpack":
        tm_label_correct = "Alone with a small backpack"
    elif travel_mode == "alone_business":
        tm_label_correct = "Alone with a business bag"
    else:  # "group_luggage"
        tm_label_correct = "In a group with luggage"

        # Frage anzeigen
    answer_tm = st.radio(
        "3. How are you traveling in this experiment?",
        options=tm_options,
        key="comprehension_alone"
    )
    
    confirm_clicked = st.form_submit_button("Confirm Answers")

if confirm_clicked:
    is_correct_price = answer_price == f"€{ticket_price:.2f}"
    is_correct_duration = answer_duration == f"{trip_duration} minutes"
    is_correct_alone = answer_tm == tm_label_correct

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
    Remember: 
    {tm_text}

    Ticket price: **{ticket_price} Euros**.  
    Each door option may offer a discount that will reduce this price.

    Total travel time: **{trip_duration}** minutes. 

    **Following train** indicates waiting for the next trip, not taking the current one. 
    """)

    
    questions = design.copy().reset_index(drop=True)

    total_questions = len(questions)

    idx = st.session_state.current_idx
    if f"temp_choice_{idx}" not in st.session_state:
        st.session_state[f"temp_choice_{idx}"] = st.session_state.responses.get(idx, "Door A")

    question = questions.iloc[idx]

    st.markdown(f"### Question {idx+1} of {total_questions}: Which door do you choose?")

    #create images

    cs_value = int(question["CS"])            # z.B. 1, 2, ..., 24
    img_num_A = (cs_value - 1) * 2 + 1        # CS=1 -> 1, CS=12 -> 23, CS=13 -> 25
    img_num_B = (cs_value - 1) * 2 + 2        # CS=1 -> 2, CS=12 -> 24, CS=13 -> 26
    
    img_path_A = os.path.join(BASE_DIR, "Figures", f"Folie{img_num_A}.png")
    img_path_B = os.path.join(BASE_DIR, "Figures", f"Folie{img_num_B}.png")




    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Door A")
        st.image(img_path_A, caption="Option A", width="content")
        st.markdown(f"**Walking distance to exit**: {question['alt1_D2E']} m")
        st.markdown(f"**Walking distance to door**: {question['alt1_D2D']} m")
        st.markdown(f"**Obstacle**: {'Yes' if question['alt1_O'] == 1 else 'No'}")
        st.markdown(f"**Crowding level at door**: {question['alt1_CD']} persons")
        st.markdown(f"**Crowding level at platform**: {question['alt1_CP']} person(s) per m²")
        # Bestimme die Beschreibung der "In-vehicle crowding"-Anzeige
        if question['alt1_CrowdingRed'] == 1 and question['alt1_CIL'] == 1 and question['alt1_CID'] != 1:
            crowding_text = "Red (LED stripe)"
        elif question['alt1_CrowdingRed'] == 1 and question['alt1_CID'] == 1 and question['alt1_CIL'] != 1:
            crowding_text = "Red (Display)"
        elif question['alt1_CrowdingRed'] == 1 and question['alt1_CIL'] == 1 and question['alt1_CID'] == 1:
            crowding_text = "Red (LED stripe & Display)"
        elif question['alt1_CrowdingGreen'] == 1 and question['alt1_CIL'] == 1 and question['alt1_CID'] != 1:
            crowding_text = "Green (LED stripe)"
        elif question['alt1_CrowdingGreen'] == 1 and question['alt1_CID'] == 1 and question['alt1_CIL'] != 1:
            crowding_text = "Green (Display)"
        elif question['alt1_CrowdingGreen'] == 1 and question['alt1_CID'] == 1 and question['alt1_CIL'] == 1:
            crowding_text = "Green (LED stripe & Display)"
        elif (
            question['alt1_CrowdingGreen'] == 0
            and question['alt1_CrowdingRed'] == 0
            and question['alt1_CIL'] == 1
            and question['alt1_CID'] != 1
        ):
            crowding_text = "Yellow (LED stripe)"
        elif (
            question['alt1_CrowdingGreen'] == 0
            and question['alt1_CrowdingRed'] == 0
            and question['alt1_CID'] == 1
            and question['alt1_CIL'] != 1
        ):
            crowding_text = "Yellow (Display)"
        elif (
            question['alt1_CrowdingGreen'] == 0
            and question['alt1_CrowdingRed'] == 0
            and question['alt1_CID'] == 1
            and question['alt1_CIL'] == 1
        ):
            crowding_text = "Yellow (LED stripe & Display)"
        else:
            crowding_text = "No information"  # Fallback, falls keine Bedingung zutrifft

        
        st.markdown(f"**In-vehicle crowding**: {crowding_text}")
        time_recent = st.session_state.get("time_recent")
        time_subseq = st.session_state.get("time_subseq")

        # Optional: als ganze Minuten formatieren, falls als float übergeben
        def fmt_minutes(x):
            return None if x is None else f"{int(round(x))} m"

        # Bedingung aus den Daten
        rc_flag = question['alt1_RC']  # 1 = nächster Zug, 0 = Folgezug

        if rc_flag == 1:
            time_text = f"{time_recent} minute(s)"
        else:
            time_text = f"{time_subseq} minutes (following train)"

        st.markdown(f"**Time until train arrival**: {time_text}")

        discount_amount_1 = round(ticket_price * question['alt1_D'] / 100, 2)
        st.markdown(f"**Offered discount**:  You pay {ticket_price * (1 - question['alt1_D']/100):.2f} Euros ({question['alt1_D']}% discount)")
    
        



    with col2:
        st.subheader("Door B")
        st.image(img_path_B, caption="Option B", width="content")
        st.markdown(f"**Walking distance to exit**: {question['alt2_D2E']} m")
        st.markdown(f"**Walking distance to door**: {question['alt2_D2D']} m")
        st.markdown(f"**Obstacle**: {'Yes' if question['alt2_O'] == 1 else 'No'}")
        st.markdown(f"**Crowding level at door**: {question['alt2_CD']} persons")
        st.markdown(f"**Crowding level at platform**: {question['alt2_CP']} person(s) per m²")
        # Bestimme die Beschreibung der "In-vehicle crowding"-Anzeige
        if question['alt2_CrowdingRed'] == 1 and question['alt2_CIL'] == 1 and question['alt2_CID'] == 0:
            crowding_text = "Red (LED stripe)"
        elif question['alt2_CrowdingRed'] == 1 and question['alt2_CID'] == 1 and question['alt2_CIL'] == 0:
            crowding_text = "Red (Display)"
        elif question ['alt2_CrowdingRed'] == 1 and question['alt2_CID'] == 1 and question['alt2_CIL'] == 1:
            crowding_text = "Red (Display & LED stripe)"
        elif question['alt2_CrowdingGreen'] == 1 and question['alt2_CIL'] == 1 and question['alt2_CID'] == 0:
            crowding_text = "Green (LED stripe)"
        elif question['alt2_CrowdingGreen'] == 1 and question['alt2_CID'] == 1 and question['alt2_CIL'] == 0:
            crowding_text = "Green (Display)"
        elif question ['alt2_CrowdingGreen'] == 1 and question['alt2_CID'] == 1 and question['alt2_CIL'] == 1:
            crowding_text = "Green (Display & LED stripe)"
        elif (
            question['alt2_CrowdingGreen'] == 0
            and question['alt2_CrowdingRed'] == 0
            and question['alt2_CIL'] == 1
            and question['alt2_CID'] == 0
        ):
            crowding_text = "Yellow (LED stripe)"
        elif (
            question['alt2_CrowdingGreen'] == 0
            and question['alt2_CrowdingRed'] == 0
            and question['alt2_CID'] == 1
            and question['alt2_CIL'] == 0
        ):
            crowding_text = "Yellow (Display)"

        elif (
            question['alt2_CrowdingGreen'] == 0
            and question['alt2_CrowdingRed'] == 0
            and question['alt2_CID'] == 1
            and question['alt2_CIL'] == 1
        ):
            crowding_text = "Yellow (Display & LED stripe)"
        else:
            crowding_text = "No information"  # Fallback, falls keine Bedingung zutrifft

        
        st.markdown(f"**In-vehicle crowding**: {crowding_text}")
        time_recent = st.session_state.get("time_recent")
        time_subseq = st.session_state.get("time_subseq")

        # Optional: als ganze Minuten formatieren, falls als float übergeben
        def fmt_minutes(x):
            return None if x is None else f"{int(round(x))} m"

        # Bedingung aus den Daten
        rc_flag = question['alt2_RC']  # 1 = nächster Zug, 0 = Folgezug

        if rc_flag == 1:
            time_text = f"{time_recent} minute(s)"
        else:
            time_text = f"{time_subseq} minutes (following train)"

        st.markdown(f"**Time until train arrival**: {time_text}")

        discount_amount_1 = round(ticket_price * question['alt2_D'] / 100, 2)
        st.markdown(f"**Offered discount**:  You pay {ticket_price * (1 - question['alt2_D']/100):.2f} Euros ({question['alt2_D']}% discount)")

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
                        'previous_transfers' : st.session_state.previous_transfers,
                        'time_recent' : st.session_state.time_recent,
                        'time_subseq' : st.session_state.time_subseq,
                        'travel_mode' : st.session_state.travel_mode,
                        'choice_set': i + 1,
                        'choice': st.session_state.responses[i],
                        'alt1_D2E': questions.iloc[i]['alt1_D2E'],
                        'alt1_D2D': questions.iloc[i]['alt1_D2D'],
                        'alt1_O': questions.iloc[i]['alt1_O'],
                        'alt1_CD': questions.iloc[i]['alt1_CD'],
                        'alt1_CP': questions.iloc[i]['alt1_CP'],
                        'alt1_CrowdingRed': questions.iloc[i]['alt1_CrowdingRed'],
                        'alt1_CrowdingGreen': questions.iloc[i]['alt1_CrowdingGreen'],
                        'alt1_CIL': questions.iloc[i]['alt1_CIL'],
                        'alt1_CID': questions.iloc[i]['alt1_CID'],
                        'alt1_D': questions.iloc[i]['alt1_D'],
                        'alt1_RC': questions.iloc[i]['alt1_RC'],       
                        'alt2_D2E': questions.iloc[i]['alt2_D2E'],
                        'alt2_D2D': questions.iloc[i]['alt2_D2D'],
                        'alt2_O': questions.iloc[i]['alt2_O'],
                        'alt2_CD': questions.iloc[i]['alt2_CD'],
                        'alt2_CP': questions.iloc[i]['alt2_CP'],
                        'alt2_CrowdingRed': questions.iloc[i]['alt2_CrowdingRed'],
                        'alt2_CrowdingGreen': questions.iloc[i]['alt2_CrowdingGreen'],
                        'alt2_CIL': questions.iloc[i]['alt2_CIL'],
                        'alt2_CID': questions.iloc[i]['alt2_CID'],
                        'alt2_D': questions.iloc[i]['alt2_D'],
                        'alt2_RC': questions.iloc[i]['alt2_RC']
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

    To better understand the survey results, we would like to ask you a few additional questions.  
    Your answers are completely voluntary, anonymous, and will only be used for academic research purposes.
    """)

    with st.form("demographics_form"):
        age = st.selectbox(
            "What is your age group?",
            ["Prefer not to say", "18–25","26-30", "31–35","36-40", "41-45","46-50","51–55", "56-60", "61–65","66-70", "71+"]
        )


        gender = st.selectbox(
            "What is your gender?",
            ["Prefer not to say", "Female", "Male", "Diverse"]
        )

        travel_freq = st.selectbox(
            "How often have you approximately traveled by **train** in the last 12 months?",
            ["Prefer not to say", "Never", "1x per day", "1x per week", "1x per month", "1x per year"]
        )

        travel_freq_1 = st.selectbox(
            "How often have you approximately traveled by ***subway*** in the last 12 months?",
            ["Prefer not to say", "Never", "1x per day", "1x per week", "1x per month", "1x per year"]
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
    
        sheet_meta = get_gsheet().worksheet("Meta")
        sheet_meta.update("A1", [[str(counter + 1)]])

        
        st.session_state.submitted_demo = True  # prevent further submissions
    
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
