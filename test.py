import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Google Sheet verbinden
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gspread"],
        scopes=scopes
    )
    gc = gspread.authorize(credentials)
    return gc.open_by_key(st.secrets["gspread"]["gsheet_key"])

st.title("Google Sheet Verbindungstest")

try:
    sheet = get_gsheet()
    worksheets = sheet.worksheets()
    st.success(f"✅ Verbindung erfolgreich! Tabellenblätter: {[s.title for s in worksheets]}")
except Exception as e:
    st.error("❌ Zugriff fehlgeschlagen")
    st.exception(e)
