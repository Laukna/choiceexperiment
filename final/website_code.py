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
if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""
if "submitted_notes" not in st.session_state:
    st.session_state.submitted_notes = False


@st.cache_data
def load_design():
    csv_path = os.path.join(BASE_DIR, "choice_sets_large.csv")
    return pd.read_csv(csv_path, sep=";")

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
    time_recent_options = [1, 2]
    travel_mode = ["alone_backpack", "alone_business", "group_luggage"] 

    rows = []
    scenario_id = 1
    for td in trip_durations:
        for tp in ticket_prices:
            for pt in previous_transfers:
                for tr in time_recent_options:
                        for tm in travel_mode:
                            rows.append(
                                {
                                    "scenario_id": scenario_id,
                                    "trip_duration": td,
                                    "ticket_price": tp,
                                    "previous_transfers": pt,
                                    "time_recent": tr,
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
st.session_state.travel_mode = scenario["travel_mode"]

ticket_price = st.session_state.ticket_price
trip_duration = st.session_state.trip_duration
previous_transfers = st.session_state.previous_transfers
time_recent = st.session_state.time_recent
travel_mode = st.session_state.travel_mode

if previous_transfers == "yes_with_change":
    pt_text = "You have already made transfers earlier in your trip. You changed doors earlier to receive discounts."
elif previous_transfers == "no":
    pt_text = "You have not made any transfers yet during this trip; this is your first boarding."
else:
    pt_text = "You have already made transfers earlier in your trip. You did not change your boarding door to receive a discount."

if travel_mode == "alone_backpack":
    tm_text = "🎒 You are traveling alone with a small backpack."
elif travel_mode == "alone_business":
    tm_text = "💼 You are traveling alone with a business bag. You have an important meeting to attend."
else:
    tm_text = "👥🧳 You are traveling in a group of 6 persons and carrying luggage."


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
Dear participant,

In this study, you will make a series of choices about where to position yourself on a train platform before boarding.
Please imagine yourself in the situation described below and make your decisions as you would in a comparable real-life situation.
There are no correct or incorrect answers.

---

**Your situation:**
For all choice tasks, assume the following:
- {tm_text}
- 💰 Regular ticket price: **{ticket_price} €**.
- ⌛️ Total trip duration: **{trip_duration} minutes**.
- {pt_text}
These conditions remain the same throughout the experiment.

---

**Decision task:**
Each choice situation presents four possible responses:
- Door L
- Door R
- Next train
- None of these options 
You decide where to wait on the platform before the train arrives.
Selecting a door implies boarding at that location.
Selecting “Next train” means skipping the upcoming train and waiting for the following one.
Selecting “None of these options” indicates that you would not choose any of the presented alternatives in this situation.

---

**Information provided:** 
Each alternative is described by several characteristics that may vary between options:
- **Walking distance to exit** — Distance from this door to the nearest exit at the destination station.
- **Walking distance to door** — Distance you walk on the platform to reach this door.
- **Obstacle** — Whether something blocks your path.
- **Crowding at door** — Number of people waiting at this door location.
- **In-vehicle crowding** — Expected crowding levels inside the train near this door (green = low, yellow = medium, red = high, gray = no information). Information may be provided via platform display, LED indicators, or both.
- **Time until train arrival** — Waiting time until the train arrives.
- **Offered discount** — Percentage reduction of the ticket price when boarding at this door.

---
**Instructions:** 
Please review all information shown for each option and select the alternative you prefer based on your own judgment.

**Examples:** """)
    example_fig_path = os.path.join(BASE_DIR, "Figures", "rectangle_exp.png")
    st.image(
        example_fig_path,
        caption="Example illustration showing how options and information are displayed. Door locations (L and R) are marked. The example includes walking distances, obstacles, crowding information, waiting time, and ticket discounts as they may appear in the tasks.",
        width="content"
    )
    
    crowding_real_fig_path = os.path.join(BASE_DIR, "Figures", "crowding_real.png")
    st.image(
        crowding_real_fig_path,
        caption="Real-world: In-vehicle crowding information shown via LED and display. ",
        width="content"
    )

    
    
    
    
    
    st.markdown(f"""

**Demographic Information:**

At the end of the survey, you will be asked a few optional demographic questions (e.g., age group, gender, travel frequency). 
These questions are voluntary and anonymous and are used for research purposes only.
                
**Data Protection and Confidentiality:**

- Your participation is entirely voluntary, and you may withdraw at any time without consequences.
- All data will be collected anonymously and used solely for academic research purposes. No personal identifiers will be recorded.
- Data storage and processing follow the requirements of the General Data Protection Regulation (GDPR/DSGVO).


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

    st.caption(f"{tm_text} | Ticket price: {ticket_price} € | Trip duration: {trip_duration} min")

    
    questions = design.copy().reset_index(drop=True)

    total_questions = len(questions)

    idx = st.session_state.current_idx
    if f"temp_choice_{idx}" not in st.session_state:
        st.session_state[f"temp_choice_{idx}"] = st.session_state.responses.get(idx, None)

    question = questions.iloc[idx]

    st.markdown(f"### Question {idx+1} of {total_questions}: Which option do you prefer?")

    #create images

    cs_value = int(question["CS"])            # z.B. 1, 2, ..., 24
    img_num = cs_value        # CS=1 -> 1, CS=12 -> 23, CS=13 -> 25
    
    img_path = os.path.join(BASE_DIR, "Figures", f"Folie{img_num}.png")


    st.image(img_path, caption="Options Door L, Door R, and Next train", use_container_width=True)

    # --- mapping: which alternative is on the LEFT in the image? (bigger D2D = further left) ---
    alt1_left = float(question["alt1_D2D"]) > float(question["alt2_D2D"])
    left_alt  = 1 if alt1_left else 2
    right_alt = 2 if alt1_left else 1
    
    def aval(alt, field):
        return question[f"alt{alt}_{field}"]
    
    def crowding_text_for(alt):
        red = aval(alt, "CrowdingRed")
        green = aval(alt, "CrowdingGreen")
        cil = aval(alt, "CIL")
        cid = aval(alt, "CID")
    
        if red == 1 and cil == 1 and cid != 1:
            return "Red (LED stripe)"
        elif red == 1 and cid == 1 and cil != 1:
            return "Red (Display)"
        elif red == 1 and cil == 1 and cid == 1:
            return "Red (LED stripe & Display)"
        elif green == 1 and cil == 1 and cid != 1:
            return "Green (LED stripe)"
        elif green == 1 and cid == 1 and cil != 1:
            return "Green (Display)"
        elif green == 1 and cil == 1 and cid == 1:
            return "Green (LED stripe & Display)"
        elif green == 0 and red == 0 and cil == 1 and cid != 1:
            return "Yellow (LED stripe)"
        elif green == 0 and red == 0 and cid == 1 and cil != 1:
            return "Yellow (Display)"
        elif green == 0 and red == 0 and cid == 1 and cil == 1:
            return "Yellow (LED stripe & Display)"
        else:
            return "No information"




    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Door L")
        st.markdown(f"**Walking distance to exit**: {aval(left_alt,'D2E')} m")
        st.markdown(f"**Walking distance to door**: {aval(left_alt,'D2D')} m")
        st.markdown(f"**Obstacle**: {'Yes' if aval(left_alt,'O') == 1 else 'No'}")
        st.markdown(f"**Crowding level at door**: {aval(left_alt,'CD')} persons")
        st.markdown(f"**In-vehicle crowding**: {crowding_text_for(left_alt)}")
        st.markdown(f"**Time until train arrival**: {time_recent} minute(s)")
        st.markdown(
            f"**Offered discount**:  You pay {ticket_price * (1 - aval(left_alt,'D')/100):.2f} € ({aval(left_alt,'D')}% discount)"
        )
    
    with col2:
        st.subheader("Door R")
        st.markdown(f"**Walking distance to exit**: {aval(right_alt,'D2E')} m")
        st.markdown(f"**Walking distance to door**: {aval(right_alt,'D2D')} m")
        st.markdown(f"**Obstacle**: {'Yes' if aval(right_alt,'O') == 1 else 'No'}")
        st.markdown(f"**Crowding level at door**: {aval(right_alt,'CD')} persons")
        st.markdown(f"**In-vehicle crowding**: {crowding_text_for(right_alt)}")
        st.markdown(f"**Time until train arrival**: {time_recent} minute(s)")
        st.markdown(
            f"**Offered discount**:  You pay {ticket_price * (1 - aval(right_alt,'D')/100):.2f} € ({aval(right_alt,'D')}% discount)"
        )


    #Option 3: Next train
    st.subheader("Next train")
    alt3_time = question["alt3_time"]
    st.markdown(f"**Time until train arrival (Next train)**: {alt3_time} minute(s)")
    alt3_discount = question["alt3_D"]
    st.markdown(
    f"**Offered discount**: You pay {ticket_price * (1 - alt3_discount/100):.2f} € ({alt3_discount}% discount)"
)



    options = ("Door L", "Door R", "Next train","None of these options")
    # Get participant's choice
    with st.form(key=f"form_{idx}"):
        st.session_state[f"temp_choice_{idx}"] = st.radio(
            "Which option do you choose?",
            options,
            index=None if st.session_state[f"temp_choice_{idx}"] is None 
                else options.index(st.session_state[f"temp_choice_{idx}"])
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

            selected = st.session_state[f"temp_choice_{idx}"]
            if selected is None:
                st.warning("Please select an option before continuing.")
                st.stop()

            if selected == "Door L":
                stored_choice = f"alt{left_alt}"
            elif selected == "Door R":
                stored_choice = f"alt{right_alt}"
            else:
                stored_choice = selected   # Next train oder None

            st.session_state.responses[idx] = stored_choice
            
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
                        'travel_mode' : st.session_state.travel_mode,
                        'CS': int(questions.iloc[i]['CS']),
                        'choice_set_in_block': i + 1,
                        'choice': st.session_state.responses[i],
                        'alt1_D2E': questions.iloc[i]['alt1_D2E'],
                        'alt1_D2D': questions.iloc[i]['alt1_D2D'],
                        'alt1_O': questions.iloc[i]['alt1_O'],
                        'alt1_CD': questions.iloc[i]['alt1_CD'],
                        'alt1_CrowdingRed': questions.iloc[i]['alt1_CrowdingRed'],
                        'alt1_CrowdingGreen': questions.iloc[i]['alt1_CrowdingGreen'],
                        'alt1_CIL': questions.iloc[i]['alt1_CIL'],
                        'alt1_CID': questions.iloc[i]['alt1_CID'],
                        'alt1_D': questions.iloc[i]['alt1_D'],      
                        'alt2_D2E': questions.iloc[i]['alt2_D2E'],
                        'alt2_D2D': questions.iloc[i]['alt2_D2D'],
                        'alt2_O': questions.iloc[i]['alt2_O'],
                        'alt2_CD': questions.iloc[i]['alt2_CD'],
                        'alt2_CrowdingRed': questions.iloc[i]['alt2_CrowdingRed'],
                        'alt2_CrowdingGreen': questions.iloc[i]['alt2_CrowdingGreen'],
                        'alt2_CIL': questions.iloc[i]['alt2_CIL'],
                        'alt2_CID': questions.iloc[i]['alt2_CID'],
                        'alt2_D': questions.iloc[i]['alt2_D'],
                        'alt3_time': questions.iloc[i]['alt3_time']
                    }
                    for i in range(total_questions)
                ])
    
                sheet_responses = get_gsheet().worksheet("Responses")
                sheet_responses.append_rows(df_responses.values.tolist(), value_input_option="USER_ENTERED")
    
                st.session_state.page = 'notes'
                st.rerun()


elif st.session_state.page == 'notes':
    st.title("Optional Notes")

    st.write("""
    You may optionally leave notes here — for example:
    - assumptions you made because some information was missing,
    - comments on the task or presentation,
    - anything you found unclear.

    This is optional. You can also leave it empty and continue.
    """)

    with st.form("notes_form"):
        notes_text = st.text_area(
            "Optional notes",
            value=st.session_state.notes_text,
            height=200,
            placeholder="Type your notes here (optional)..."
        )

        col_back, col_next = st.columns([1, 5])
        with col_back:
            back_clicked = st.form_submit_button("Back")
        with col_next:
            next_clicked = st.form_submit_button("Continue")

    if back_clicked:
        # zurück zur letzten Survey-Seite (Index bleibt unverändert)
        st.session_state.page = 'survey'
        st.rerun()

    if next_clicked and not st.session_state.get("submitted_notes", False):
        st.session_state.notes_text = notes_text

        # In Google Sheet speichern (Worksheet muss existieren: "Notes")
        notes_df = pd.DataFrame([{
            "participant_number": counter,
            "notes": notes_text
        }])

        sheet_notes = get_gsheet().worksheet("Notes")
        sheet_notes.append_rows(notes_df.values.tolist(), value_input_option="USER_ENTERED")

        st.session_state.submitted_notes = True

        st.session_state.page = 'demographics'
        st.rerun()


elif st.session_state.page == 'demographics':
    st.title("A Few More Questions")
    st.write("""

    To better understand the survey results, we would like to ask you a few additional questions.  
    These questions are voluntary and anonymous and are used for research purposes only.
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

    If you have any questions or would like to know more about this research, please contact:

    Laura Knappik
    
    RWTH Aachen University  
    
    knappik@analytics.rwth-aachen.de

    ---

    You may now close this tab or window.

    """)
