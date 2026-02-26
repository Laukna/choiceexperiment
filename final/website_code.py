import streamlit as st
import pandas as pd
import os
import json
#import gspread
#from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw
import uuid
from datetime import datetime, timezone
#from gspread.utils import rowcol_to_a1
import hashlib
import psycopg2


# Base directory for relative assets (folder containing this script)
BASE_DIR = os.path.dirname(__file__)


#@st.cache_resource
# def get_gsheet():
#     from google.oauth2.service_account import Credentials
#     import gspread

#     credentials_dict = dict(st.secrets["gspread"])  # convert TOML object to dict
#     scopes = [
#         "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive"
#     ]
#     credentials = Credentials.from_service_account_info(
#         credentials_dict,
#         scopes=scopes
#     )
#     gc = gspread.authorize(credentials)
#     return gc.open_by_key(credentials_dict["gsheet_key"])

@st.cache_resource
def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")

@st.cache_resource
def ensure_tables():
    conn = get_db()
    with conn.cursor() as cur:
        # participants
        cur.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            participant_id TEXT PRIMARY KEY,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            cs_group TEXT,
            scenario_id INTEGER,
            current_idx INTEGER,
            responses_json TEXT
        );
        """)
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS demographics_json TEXT;")
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS notes TEXT;")
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS current_page TEXT;")

        # demographics as real columns (instead of json)
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS demo_age TEXT;")
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS demo_gender TEXT;")
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS demo_trainfq TEXT;")
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS demo_subwayfq TEXT;")
        cur.execute("ALTER TABLE participants ADD COLUMN IF NOT EXISTS demo_mobility TEXT;")

        # responses (BASE TABLE: lowercase column names)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            participant_id TEXT NOT NULL,
            choice_set_in_block INTEGER NOT NULL,
            choice TEXT,
            updated_at TEXT,
            PRIMARY KEY (participant_id, choice_set_in_block)
        );
        """)

        # Add all "Google-Sheet-like" fields (lowercase in table)
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS cs INTEGER;")

        # context
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS ticket_price DOUBLE PRECISION;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS trip_duration INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS previous_transfers TEXT;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS time_recent INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS travel_mode TEXT;")

        # alt1
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_d2e INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_d2d INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_cp INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_cd INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_crowdingred INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_crowdinggreen INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_cil INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_cid INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt1_d DOUBLE PRECISION;")

        # alt2
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_d2e INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_d2d INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_cp INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_cd INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_crowdingred INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_crowdinggreen INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_cil INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_cid INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt2_d DOUBLE PRECISION;")

        # alt3
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt3_time INTEGER;")
        cur.execute("ALTER TABLE responses ADD COLUMN IF NOT EXISTS alt3_d DOUBLE PRECISION;")

        # VIEW: exakt wie Google Sheets "Responses" Header (inkl. Groß-/Kleinschreibung)
        cur.execute("""
        CREATE OR REPLACE VIEW responses_gsheet AS
        SELECT
            participant_id                                  AS "participant_id",
            cs                                              AS "CS",
            choice_set_in_block                              AS "choice_set_in_block",
            choice                                          AS "choice",
            updated_at                                      AS "updated_at",

            ticket_price                                    AS "ticket_price",
            trip_duration                                   AS "trip_duration",
            previous_transfers                              AS "previous_transfers",
            time_recent                                     AS "time_recent",
            travel_mode                                     AS "travel_mode",

            alt1_d2e                                        AS "alt1_D2E",
            alt1_d2d                                        AS "alt1_D2D",
            alt1_cp                                         AS "alt1_CP",
            alt1_cd                                         AS "alt1_CD",
            alt1_crowdingred                                AS "alt1_CrowdingRed",
            alt1_crowdinggreen                              AS "alt1_CrowdingGreen",
            alt1_cil                                        AS "alt1_CIL",
            alt1_cid                                        AS "alt1_CID",
            alt1_d                                          AS "alt1_D",

            alt2_d2e                                        AS "alt2_D2E",
            alt2_d2d                                        AS "alt2_D2D",
            alt2_cp                                         AS "alt2_CP",
            alt2_cd                                         AS "alt2_CD",
            alt2_crowdingred                                AS "alt2_CrowdingRed",
            alt2_crowdinggreen                              AS "alt2_CrowdingGreen",
            alt2_cil                                        AS "alt2_CIL",
            alt2_cid                                        AS "alt2_CID",
            alt2_d                                          AS "alt2_D",

            alt3_time                                       AS "alt3_time",
            alt3_d                                          AS "alt3_D"
        FROM responses;
        """)

    conn.commit()
    return True

# call once per process
try:
    ensure_tables()
except Exception as e:
    st.error(f"DB table creation failed: {e}")



# def find_row_by_keys(ws, header, key_cols, key_vals):
#     # Build column indices
#     col_idx = {name: i + 1 for i, name in enumerate(header)}
#     key_col_indices = [col_idx[c] for c in key_cols]

#     # Read only key columns (excluding header)
#     # Note: get_all_values can be heavy; for moderate sheet sizes it's ok.
#     data = ws.get_all_values()
#     if not data:
#         return None
#     rows = data[1:]  # skip header
#     for i, r in enumerate(rows, start=2):  # actual sheet row number
#         ok = True
#         for kc_i, kv in zip(key_col_indices, key_vals):
#             cell = r[kc_i - 1] if kc_i - 1 < len(r) else ""
#             if str(cell) != str(kv):
#                 ok = False
#                 break
#         if ok:
#             return i
#     return None


# def upsert_row(ws, key_cols, key_vals, row_dict):

#     data = ws.get_all_values()
#     if not data:
#         raise ValueError(f"Worksheet {ws.title} has no header row.")
#     header = data[0]

#     # Ensure all columns exist
#     missing = [c for c in row_dict.keys() if c not in header]
#     if missing:
#         raise ValueError(f"Missing columns in {ws.title}: {missing}")

#     # Prepare full row in header order
#     full_row = [row_dict.get(col, "") for col in header]

#     row_idx = find_row_by_keys(ws, header, key_cols, key_vals)
#     if row_idx is None:
#         ws.append_row(full_row, value_input_option="USER_ENTERED")
#     else:
#         # Update the entire row range (A..lastcol)
#         start = rowcol_to_a1(row_idx, 1)
#         end = rowcol_to_a1(row_idx, len(header))
#         ws.update(f"{start}:{end}", [full_row])

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

# def flush_all_responses_to_gsheet():
#     if st.session_state.get("responses_flushed", False):
#         return
#     pid = st.session_state.participant_id

#     questions = st.session_state.questions_df
#     total_questions = len(questions)

#     # Sicherheitscheck: sind wirklich alle beantwortet?
#     missing = [i for i in range(total_questions) if st.session_state.responses.get(i, None) is None]
#     if missing:
#         raise ValueError(f"Not all questions answered. Missing indices: {missing}")

#     sheet = get_gsheet()
#     ws_resp = sheet.worksheet("Responses")

#     header = ws_resp.row_values(1)

#     rows = []
#     ts = now_utc_iso()

#     for i, q in questions.iterrows():
#         row_dict = {
#             "participant_id": pid,
#             "CS": int(q["CS"]),
#             "choice_set_in_block": int(i + 1),
#             "choice": st.session_state.responses[i],
#             "updated_at": ts,

#             # Kontext
#             "ticket_price": st.session_state.ticket_price,
#             "trip_duration": st.session_state.trip_duration,
#             "previous_transfers": st.session_state.previous_transfers,
#             "time_recent": st.session_state.time_recent,
#             "travel_mode": st.session_state.travel_mode,

#             # Attribute
#             "alt1_D2E": int(q["alt1_D2E"]),
#             "alt1_D2D": int(q["alt1_D2D"]),
#             "alt1_CP": int(q["alt1_CP"]),
#             "alt1_CD": int(q["alt1_CD"]),
#             "alt1_CrowdingRed": int(q["alt1_CrowdingRed"]),
#             "alt1_CrowdingGreen": int(q["alt1_CrowdingGreen"]),
#             "alt1_CIL": int(q["alt1_CIL"]),
#             "alt1_CID": int(q["alt1_CID"]),
#             "alt1_D": float(q["alt1_D"]),

#             "alt2_D2E": int(q["alt2_D2E"]),
#             "alt2_D2D": int(q["alt2_D2D"]),
#             "alt2_CP": int(q["alt2_CP"]),
#             "alt2_CD": int(q["alt2_CD"]),
#             "alt2_CrowdingRed": int(q["alt2_CrowdingRed"]),
#             "alt2_CrowdingGreen": int(q["alt2_CrowdingGreen"]),
#             "alt2_CIL": int(q["alt2_CIL"]),
#             "alt2_CID": int(q["alt2_CID"]),
#             "alt2_D": float(q["alt2_D"]),

#             "alt3_time": int(q["alt3_time"]),
#             "alt3_D": float(q["alt3_D"]),
#         }

#         rows.append([row_dict.get(col, "") for col in header])

#     ws_resp.append_rows(rows, value_input_option="USER_ENTERED")
#     st.session_state.responses_flushed = True



# --- GLOBAL HEADER WITH LOGO ---

logo_path = os.path.join(BASE_DIR, "Figures", "rwth_lehrstuhl_fuer_data_and_business_analytics_de_rgb.svg")

col_left, col_center, col_right = st.columns([1,2,1])

with col_center:
    st.image(logo_path, width=500)  

st.markdown("---")

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
if "final_submitted" not in st.session_state:
    st.session_state.final_submitted = False
if "started_at" not in st.session_state:
    st.session_state.started_at = None
if "responses_flushed" not in st.session_state:
    st.session_state.responses_flushed = False

qp = st.query_params
pid_from_url = qp.get("pid")

if "participant_id" not in st.session_state:
    if pid_from_url:
        st.session_state.participant_id = str(pid_from_url)
    else:
        st.session_state.participant_id = str(uuid.uuid4())
        st.query_params["pid"] = st.session_state.participant_id
else:
    st.query_params["pid"] = st.session_state.participant_id


@st.cache_data
def load_design():
    csv_path = os.path.join(BASE_DIR, "choice_sets_large.csv")
    return pd.read_csv(csv_path, sep=",")

design = load_design()

def save_progress_db(current_idx_to_store: int, page_to_store: str):
    conn = get_db()
    pid = st.session_state.participant_id
    ts = now_utc_iso()

    if st.session_state.started_at is None:
        st.session_state.started_at = ts

    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO participants
            (participant_id, started_at, finished_at, status, cs_group, scenario_id, current_idx, responses_json, current_page)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (participant_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            current_idx = EXCLUDED.current_idx,
            responses_json = EXCLUDED.responses_json,
            current_page = EXCLUDED.current_page;
        """, (
            pid,
            st.session_state.started_at,
            None,
            "in_progress",
            st.session_state.cs_group,
            int(st.session_state.scenario_id),
            int(current_idx_to_store),
            json.dumps(st.session_state.responses),
            page_to_store,
        ))
    conn.commit()


def upsert_response_db(idx: int, question_row, stored_choice: str):
    conn = get_db()
    pid = st.session_state.participant_id
    ts = now_utc_iso()

    choice_set_in_block = int(idx + 1)  # 1-basiert

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO responses (
                participant_id, choice_set_in_block, choice, updated_at,
                cs,
                ticket_price, trip_duration, previous_transfers, time_recent, travel_mode,
                alt1_d2e, alt1_d2d, alt1_cp, alt1_cd, alt1_crowdingred, alt1_crowdinggreen, alt1_cil, alt1_cid, alt1_d,
                alt2_d2e, alt2_d2d, alt2_cp, alt2_cd, alt2_crowdingred, alt2_crowdinggreen, alt2_cil, alt2_cid, alt2_d,
                alt3_time, alt3_d
            )
            VALUES (
                %s, %s, %s, %s,
                %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (participant_id, choice_set_in_block)
            DO UPDATE SET
                choice=EXCLUDED.choice,
                updated_at=EXCLUDED.updated_at,

                cs=EXCLUDED.cs,
                ticket_price=EXCLUDED.ticket_price,
                trip_duration=EXCLUDED.trip_duration,
                previous_transfers=EXCLUDED.previous_transfers,
                time_recent=EXCLUDED.time_recent,
                travel_mode=EXCLUDED.travel_mode,

                alt1_d2e=EXCLUDED.alt1_d2e,
                alt1_d2d=EXCLUDED.alt1_d2d,
                alt1_cp=EXCLUDED.alt1_cp,
                alt1_cd=EXCLUDED.alt1_cd,
                alt1_crowdingred=EXCLUDED.alt1_crowdingred,
                alt1_crowdinggreen=EXCLUDED.alt1_crowdinggreen,
                alt1_cil=EXCLUDED.alt1_cil,
                alt1_cid=EXCLUDED.alt1_cid,
                alt1_d=EXCLUDED.alt1_d,

                alt2_d2e=EXCLUDED.alt2_d2e,
                alt2_d2d=EXCLUDED.alt2_d2d,
                alt2_cp=EXCLUDED.alt2_cp,
                alt2_cd=EXCLUDED.alt2_cd,
                alt2_crowdingred=EXCLUDED.alt2_crowdingred,
                alt2_crowdinggreen=EXCLUDED.alt2_crowdinggreen,
                alt2_cil=EXCLUDED.alt2_cil,
                alt2_cid=EXCLUDED.alt2_cid,
                alt2_d=EXCLUDED.alt2_d,

                alt3_time=EXCLUDED.alt3_time,
                alt3_d=EXCLUDED.alt3_d;
        """, (
            pid, choice_set_in_block, str(stored_choice), ts,
            int(question_row["CS"]),

            float(st.session_state.ticket_price),
            int(st.session_state.trip_duration),
            str(st.session_state.previous_transfers),
            int(st.session_state.time_recent),
            str(st.session_state.travel_mode),

            int(question_row["alt1_D2E"]),
            int(question_row["alt1_D2D"]),
            int(question_row["alt1_CP"]),
            int(question_row["alt1_CD"]),
            int(question_row["alt1_CrowdingRed"]),
            int(question_row["alt1_CrowdingGreen"]),
            int(question_row["alt1_CIL"]),
            int(question_row["alt1_CID"]),
            float(question_row["alt1_D"]),

            int(question_row["alt2_D2E"]),
            int(question_row["alt2_D2D"]),
            int(question_row["alt2_CP"]),
            int(question_row["alt2_CD"]),
            int(question_row["alt2_CrowdingRed"]),
            int(question_row["alt2_CrowdingGreen"]),
            int(question_row["alt2_CIL"]),
            int(question_row["alt2_CID"]),
            float(question_row["alt2_D"]),

            int(question_row["alt3_time"]),
            float(question_row["alt3_D"]),
        ))
    conn.commit()
# Get participant counter from Google Sheet
# if 'counter' not in st.session_state:
#     sheet_meta = get_gsheet().worksheet("Meta")
#     counter_cell = sheet_meta.acell("A1").value
#     st.session_state.counter = int(counter_cell)

# counter = st.session_state.counter

# #Split choice sets into two groups 
# if 'cs_group' not in st.session_state:
#     st.session_state.cs_group = 'A' if counter % 2 == 1 else 'B'

# cs_group = st.session_state.cs_group

pid = st.session_state.participant_id
pid_int = int(hashlib.md5(pid.encode("utf-8")).hexdigest(), 16)

if 'cs_group' not in st.session_state:
    st.session_state.cs_group = 'A' if (pid_int % 2 == 0) else 'B'

cs_group = st.session_state.cs_group

# Check Boarding.csv -> column called CS?
if cs_group == 'A':
    design = design[design['CS'].between(1, 12)].sort_values("CS").copy()
else:
    design = design[design['CS'].between(13, 24)].sort_values("CS").copy()
# Fix questions for this participant/session (prevents reordering changes across reruns)
# Fix questions for this participant/session (prevents reordering changes across reruns)
if "questions_df" not in st.session_state:
    st.session_state.questions_df = design.reset_index(drop=True).copy()

# # Restore progress once per session (from Participants sheet)
# if "progress_loaded" not in st.session_state:
#     try:
#         ws_part = get_gsheet().worksheet("Participants")
#         data = ws_part.get_all_values()
#         if data and len(data) > 1:
#             header = data[0]
#             col = {name: i for i, name in enumerate(header)}
#             pid = st.session_state.participant_id

#             row = None
#             for r in data[1:]:
#                 if len(r) > col.get("participant_id", 10**9) and r[col["participant_id"]] == pid:
#                     row = r
#                     break
#             if row and "started_at" in col and len(row) > col["started_at"] and row[col["started_at"]].strip():
#                 st.session_state.started_at = row[col["started_at"]].strip()

#             if row and "responses_json" in col and len(row) > col["responses_json"]:
#                 raw = row[col["responses_json"]].strip()
#                 if raw:
#                     loaded = json.loads(raw)
#                     st.session_state.responses = {int(k): v for k, v in loaded.items()}

#             # Prefer first unanswered index
#             total = len(st.session_state.questions_df)
#             first_missing = None
#             for i in range(total):
#                 if st.session_state.responses.get(i, None) is None:
#                     first_missing = i
#                     break
#             if first_missing is not None:
#                 st.session_state.current_idx = first_missing
#             # AUTO resume into survey if progress exists
#             if st.session_state.responses:
#                 st.session_state.page = "survey"
#     except Exception:
#         pass  # keep it minimal: if load fails, just start normally

#     st.session_state.progress_loaded = True

# Restore progress once per session (from PostgreSQL)
# Restore progress once per session (from PostgreSQL)
# Restore progress once per session (from PostgreSQL)
# Restore progress once per session (from PostgreSQL)
if "progress_loaded" not in st.session_state:
    try:
        conn = get_db()
        pid = st.session_state.participant_id

        with conn.cursor() as cur:
            cur.execute(
                "SELECT started_at, status, current_idx, current_page, responses_json "
                "FROM participants WHERE participant_id=%s",
                (pid,)
            )
            row = cur.fetchone()

        if row:
            started_at, status, current_idx, current_page, responses_json = row

            if started_at:
                st.session_state.started_at = started_at

            if responses_json:
                loaded = json.loads(responses_json)
                st.session_state.responses = {int(k): v for k, v in loaded.items()}

            # Index wiederherstellen (DB ist Quelle der Wahrheit)
            if current_idx is not None:
                st.session_state.current_idx = int(current_idx)
            else:
                # fallback: first unanswered
                total = len(st.session_state.questions_df)
                for i in range(total):
                    if st.session_state.responses.get(i, None) is None:
                        st.session_state.current_idx = i
                        break

            # Seite wiederherstellen
            if current_page:
                st.session_state.page = current_page
            else:
                st.session_state.page = "survey" if (status in ("started", "in_progress") or st.session_state.responses) else "start"

            # completed -> end
            if status == "completed":
                st.session_state.page = "end"

    except Exception as e:
        st.warning(f"DB restore failed (starting fresh): {e}")

    st.session_state.progress_loaded = True

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
scenario_idx = pid_int % n_scenarios
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
Dear participant,

You will be presented with several scenarios in which you choose the boarding door you would use to board a subway train. Please imagine yourself in the situation described below and make your decisions as you would in a comparable real-life situation. There are no correct or incorrect answers.

---

**Your situation:**
For all questions, assume the following:
- {tm_text}
- Regular ticket price: **{ticket_price:.2f} €**.
- Total trip duration: **{trip_duration} minutes**.
- {pt_text}
- Your (upcoming) train will depart in **{time_recent} minutes**.

These conditions remain the same throughout the experiment.

---

**Decision task:**
Each question presents four possible responses:
- Door L (left)
- Door R (right)
- Next train
- None of these options 

You choose which door to use for boarding the subway train. 
Selecting a door implies boarding at that location.
Selecting “Next train” means skipping the upcoming train and waiting for the following one.
Selecting “None of these options” indicates that you would not choose any of the presented alternatives in this situation.

---

**Information provided:** 

Each alternative is described by several attributes that may vary between options:
- **Walking distance to exit** — Distance from this door to the nearest exit at the destination station.
- **Walking distance to door** — Distance you walk on the platform to reach this door.
- **Crowding on platform** — Whether the platform is crowded or not.
- **Crowding at door** — Number of people waiting at this door location.
- **In-vehicle crowding** — Expected crowding levels inside the train near this door (green = low, yellow = medium, red = high, gray = no information). Information may be provided via platform display, LED indicators, or both.
- **Offered discount** — Percentage reduction of the ticket price when boarding at this door.

---
**Instructions:** 
Please review all information shown for each option and select the alternative you prefer based on your own judgment.

**Examples:** """)
    example_fig_path = os.path.join(BASE_DIR, "Figures", "Folie12.png")
    st.image(
        example_fig_path,
        caption="Example illustration showing how options and information are displayed. Door locations (L and R) are marked. The example includes crowding information, waiting time, and ticket discounts as they may appear in the tasks.",
        width="content"
    )
    
    crowding_real_fig_path = os.path.join(BASE_DIR, "Figures", "crowding_real.png")
    st.image(
        crowding_real_fig_path,
        caption="Real-world: In-vehicle crowding information shown via LED and display. ",
        width="content"
    )

    crowding_exp_fig_path = os.path.join(BASE_DIR, "Figures", "example_invehicle.png")
    st.image(
        crowding_exp_fig_path,
        caption="In-vehicle crowding information is communicated via alternative information channels (LED guidance or platform display). In this example, Door R shows green crowding information via LED guidance, while no information is provided via the display (gray indicates absence of information).",
        width="content"
    )

    
    
    
    
    
    st.markdown(f"""

**Demographic Information:**

At the end of the survey, you will be asked a few optional demographic questions (e.g., age group, gender, travel frequency). 
These questions are voluntary and anonymous and are used for research purposes only.
""")
               
    with st.expander("Data Protection and Confidentiality", expanded=False):
        st.markdown("""
This study is conducted in accordance with the General Data Protection Regulation (GDPR).

**Data collection and purpose**  
Only research-relevant data are collected (experimental choices, scenario parameters, optional demographic information, and optional comments). No direct personal identifiers (e.g., name or email) are recorded. Participants are identified only via a pseudonymous participant ID.

**Legal basis**  
Data processing is based on informed consent (Art. 6(1)(a) GDPR). Participation is voluntary and may be discontinued at any time without consequences.

**Data storage and retention**  
Data are primarily stored on secure servers within the European Union (Frankfurt region). The application is hosted via Render; processing may involve infrastructure outside the EEA under appropriate safeguards (e.g., Standard Contractual Clauses) ensuring GDPR-compliant protection. Research data are retained for scientific documentation and reproducibility for up to 10 years and then deleted or anonymized.

**Access and rights**  
Data access is restricted to authorized researchers. Participants have the right to withdraw consent and to request access, correction, or deletion where applicable under GDPR.

**Contact**  
RWTH Aachen University – Chair of Data & Business Analytics  
knappik@analytics.rwth-aachen.de
""")
    st.markdown(f"""
**Contact Information:**

If you have any questions about the study, please contact **Laura Knappik** at **knappik@analytics.rwth-aachen.de**.


---

By continuing, you confirm that you are 18+ years old, have read and understood the information provided above, and agree to participate under these conditions.
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

        pid = st.session_state.participant_id
        if st.session_state.started_at is None:
            st.session_state.started_at = now_utc_iso()

        # Also mark started in PostgreSQL
        try:
            # start markieren + page speichern
            st.session_state.page = "survey"
            st.session_state.current_idx = 0
            save_progress_db(0, "survey")
        except Exception as e:
            st.warning(f"Could not mark start in DB: {e}")

        st.rerun()




# --- SURVEY PAGE ---

elif st.session_state.page == 'survey':
    st.title("Train Door Choice Survey")

    st.caption(f"{tm_text} | Ticket price: {ticket_price} € | Trip duration: {trip_duration} min | Departure time: {time_recent} min")  

    
    questions = st.session_state.questions_df

    total_questions = len(questions)
    idx = st.session_state.current_idx

    

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

    #idx = st.session_state.current_idx

    # Map stored choice -> label, so Back shows the last saved selection
    # Initialize preselection only once per question (prevents UI flicker on reruns)
    if f"temp_choice_{idx}" not in st.session_state:
        stored = st.session_state.responses.get(idx, None)
        if stored == f"alt{left_alt}":
            st.session_state[f"temp_choice_{idx}"] = "Door L"
        elif stored == f"alt{right_alt}":
            st.session_state[f"temp_choice_{idx}"] = "Door R"
        else:
            st.session_state[f"temp_choice_{idx}"] = stored  # "Next train", "None..." or None
    
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
        st.markdown(f"**Walking distance from door to exit**: {aval(left_alt,'D2E')} m")
        st.markdown(f"**Walking distance to door**: {aval(left_alt,'D2D')} m")
        st.markdown(f"**Crowding on platform**: {'Yes' if aval(left_alt,'CP') == 1 else 'No'}")
        st.markdown(f"**Crowding level at door**: {aval(left_alt,'CD')} persons")
        st.markdown(f"**In-vehicle crowding**: {crowding_text_for(left_alt)}")
        st.markdown(
            f"**Offered discount**:  You pay {ticket_price * (1 - aval(left_alt,'D')/100):.2f} € ({aval(left_alt,'D')}% discount)"
        )
    
    with col2:
        st.subheader("Door R")
        st.markdown(f"**Walking distance from door to exit**: {aval(right_alt,'D2E')} m")
        st.markdown(f"**Walking distance to door**: {aval(right_alt,'D2D')} m")
        st.markdown(f"**Crowding on platform**: {'Yes' if aval(right_alt,'CP') == 1 else 'No'}")
        st.markdown(f"**Crowding level at door**: {aval(right_alt,'CD')} persons")
        st.markdown(f"**In-vehicle crowding**: {crowding_text_for(right_alt)}")
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
            next_clicked = st.form_submit_button("Next" if idx < total_questions - 1 else "Continue")
    
        if back_clicked and idx > 0:
            selected = st.session_state[f"temp_choice_{idx}"]
            if selected is None:
                # wenn nichts gewählt wurde: einfach nur zurück
                save_progress_db(idx - 1, "survey")
                st.session_state.current_idx -= 1
                st.rerun()

            # stored_choice bestimmen (wie bei Next)
            if selected == "Door L":
                stored_choice = f"alt{left_alt}"
            elif selected == "Door R":
                stored_choice = f"alt{right_alt}"
            else:
                stored_choice = selected

            st.session_state.responses[idx] = stored_choice

            # Antwort + Attribute speichern
            try:
                upsert_response_db(idx, question, stored_choice)
            except Exception as e:
                st.error(f"Could not save response + attributes to DB. Error: {e}")
                st.stop()

            # aktuellen Stand speichern (aktuelle Frage = idx)
            try:
                save_progress_db(idx - 1, "survey")
            except Exception as e:
                st.error(f"Could not save progress. Error: {e}")
                st.stop()

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

            # Long-format persistieren (idx ist 0-basiert -> DB will 1-basiert)
            # Antwort + Attribute in responses upserten
            try:
                upsert_response_db(idx, question, stored_choice)
            except Exception as e:
                st.error(f"Could not save response + attributes to DB. Error: {e}")
                st.stop()

            # Autosave progress to Participants every N questions (fast)
            # N = 1  # z.B. 3; nimm 1 wenn es dich nicht stört
            # if (idx + 1) % N == 0:
            #     try:
            #         ws_part = get_gsheet().worksheet("Participants")
            #         upsert_row(
            #             ws_part,
            #             key_cols=["participant_id"],
            #             key_vals=[st.session_state.participant_id],
            #             row_dict={
            #                 "participant_id": st.session_state.participant_id,
            #                 "started_at": st.session_state.started_at,
            #                 "finished_at": "",
            #                 "status": "in_progress",
            #                 "cs_group": st.session_state.cs_group,
            #                 "scenario_id": st.session_state.scenario_id,
            #                 "current_idx": int(idx + 1),
            #                 "responses_json": json.dumps(st.session_state.responses),
            #                 "updated_at": now_utc_iso(),
            #             }
            #         )
            #     except Exception:
            #         pass
            
            # Save progress to PostgreSQL (fast upsert)
            try:
                save_progress_db(idx + 1, "survey")
            except Exception as e:
                st.error(f"Could not save progress. Please try again. Error: {e}")
                st.stop()

            # Weiter zur nächsten Frage / oder weiter zu demographics am Ende
            if idx < total_questions - 1:
                st.session_state.current_idx += 1
                st.rerun()
            else:
                # am Ende: optional noch alles final wegschreiben
                # (solange du noch Google Sheets nutzt)
                save_progress_db(idx + 1, "demographics")
                st.session_state.page = "demographics"
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
            ["Prefer not to say", "18–25","26-30", "31–35","36-40", "41-45","46-50","51–55", "56-60", "61–65","66-70", "71+"], key="demo_age"
        )


        gender = st.selectbox(
            "What is your gender?",
            ["Prefer not to say", "Female", "Male", "Diverse"], key="demo_gender"
        )

        travel_freq = st.selectbox(
            "How often have you approximately traveled by **train** in the last 12 months?",
            ["Prefer not to say", "Never", "1x per day", "1x per week", "1x per month", "1x per year"], key="demo_trainfq"
        )

        travel_freq_1 = st.selectbox(
            "How often have you approximately traveled by ***subway*** in the last 12 months?",
            ["Prefer not to say", "Never", "1x per day", "1x per week", "1x per month", "1x per year"], key="demo_subwayfq"
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
            ], key="demo_mobility"
        )

        col_back, col_submit = st.columns([1, 5])
        with col_back:
            back_clicked = st.form_submit_button("Back")
        with col_submit:
            submitted = st.form_submit_button("Continue")

    if back_clicked:
        save_progress_db(st.session_state.current_idx, "survey")
        st.session_state.page = 'survey'
        st.rerun()
        # Make sure this is at the same level as the other inputs
        #submitted = st.form_submit_button("Submit Demographic Data")

    if submitted:
        pid = st.session_state.participant_id
        demo = {
            "age": st.session_state.get("demo_age", "Prefer not to say"),
            "gender": st.session_state.get("demo_gender", "Prefer not to say"),
            "travel_frequency": st.session_state.get("demo_trainfq", "Prefer not to say"),
            "ubahn_frequency": st.session_state.get("demo_subwayfq", "Prefer not to say"),
            "mobility": st.session_state.get("demo_mobility", "Prefer not to say"),
        }

        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE participants
                SET
                    demo_age=%s,
                    demo_gender=%s,
                    demo_trainfq=%s,
                    demo_subwayfq=%s,
                    demo_mobility=%s
                WHERE participant_id=%s
            """, (
                st.session_state.get("demo_age"),
                st.session_state.get("demo_gender"),
                st.session_state.get("demo_trainfq"),
                st.session_state.get("demo_subwayfq"),
                st.session_state.get("demo_mobility"),
                pid
            ))
        conn.commit()

        save_progress_db(st.session_state.current_idx, "notes")

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

    # ✅ Back button OUTSIDE the form (does NOT submit the form)
    if st.button("Back", key="notes_back"):
        save_progress_db(st.session_state.current_idx, "demographics")
        st.session_state.page = 'demographics'
        st.rerun()

    # ✅ Only one submit inside the form
    with st.form("notes_form"):
        notes_text = st.text_area(
            "Optional notes",
            value=st.session_state.notes_text,
            height=200,
            placeholder="Type your notes here (optional)..."
        )

        submitted = st.form_submit_button("Submit")

    if submitted:


        st.session_state.notes_text = notes_text
        st.session_state.final_submitted = True

        pid = st.session_state.participant_id
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE participants
                SET notes=%s
                WHERE participant_id=%s
            """, (st.session_state.notes_text, pid))
        conn.commit()

        

        # Mark completed in PostgreSQL
        try:
            conn = get_db()
            pid = st.session_state.participant_id
            ts = now_utc_iso()
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE participants
                SET finished_at=%s,
                    status=%s,
                    current_idx=%s,
                    responses_json=%s,
                    current_page=%s
                WHERE participant_id=%s
                """, (
                    ts,
                    "completed",
                    int(st.session_state.current_idx),
                    json.dumps(st.session_state.responses),
                    "end",
                    pid
                ))
            conn.commit()
        except Exception as e:
            st.warning(f"Could not mark completion in DB: {e}")

        save_progress_db(st.session_state.current_idx, "end")
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
