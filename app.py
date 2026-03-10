import io
import contextlib
import traceback

import streamlit as st
from streamlit_ace import st_ace
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Python Notes Code Editor", layout="wide")


# =========================
# Google Sheets Connection
# =========================
def connect_to_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)

    # Your spreadsheet ID from the link you shared
    sheet = client.open_by_key("14pnlZ5jfXNC-AGrSsRQAmUQ17Acbn5xxDZQMsAlJQlo")

    # Uses the first tab in the spreadsheet
    worksheet = sheet.sheet1

    return worksheet


# =========================
# Session State Setup
# =========================
if "editor_text" not in st.session_state:
    st.session_state.editor_text = ""

if "console_output" not in st.session_state:
    st.session_state.console_output = ""

if "console_error" not in st.session_state:
    st.session_state.console_error = ""


# =========================
# Button Functions
# =========================
def clear_console():
    st.session_state.console_output = ""
    st.session_state.console_error = ""


def run_code():
    code_to_run = st.session_state.editor_text
    stdout_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(code_to_run, {})
        st.session_state.console_output = stdout_buffer.getvalue()
        st.session_state.console_error = ""
    except Exception:
        st.session_state.console_output = stdout_buffer.getvalue()
        st.session_state.console_error = traceback.format_exc()


def save_to_google_sheets(category, concept, code_example, output_text, explanation, notes):
    try:
        worksheet = connect_to_sheet()

        new_row = [
            category,
            concept,
            code_example,
            output_text,
            explanation,
            notes
        ]

        worksheet.append_row(new_row)
        return True, "Saved to Google Sheets!"
    except Exception as e:
        return False, f"Error saving to Google Sheets: {e}"


# =========================
# App UI
# =========================
st.title("Python Notes Code Editor")
st.write("Write Python code, run it, and save your notes to Google Sheets.")


# =========================
# Note Fields
# =========================
st.subheader("Note Entry")

col_a, col_b = st.columns(2)

with col_a:
    category = st.text_input("Category")

with col_b:
    concept = st.text_input("Concept")


# =========================
# Code Editor
# =========================
st.subheader("Code Example")

editor_value = st_ace(
    value=st.session_state.editor_text,
    language="python",
    theme="monokai",
    key="ace_editor",
    height=400,
    font_size=14,
    tab_size=4,
    show_gutter=True,
    wrap=True,
    auto_update=True,
)

st.session_state.editor_text = editor_value if editor_value is not None else ""


# =========================
# Buttons
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.button("Run Code", on_click=run_code)

with col2:
    st.button("Clear Console", on_click=clear_console)

with col3:
    st.download_button(
        label="Download Code",
        data=st.session_state.editor_text,
        file_name="example.py",
        mime="text/plain"
    )


# =========================
# Console Output
# =========================
st.subheader("Console")
st.code(st.session_state.console_output or "", language="text")

if st.session_state.console_error:
    st.subheader("Errors")
    st.code(st.session_state.console_error, language="text")


# =========================
# Remaining Note Fields
# =========================
st.subheader("Additional Fields")

output_text = st.text_area(
    "Output / Result",
    value=st.session_state.console_output,
    height=120
)

explanation = st.text_area(
    "Explanation",
    height=160
)

notes = st.text_area(
    "Notes",
    height=160
)


# =========================
# Save to Google Sheets
# =========================
if st.button("Save to Google Sheets"):
    success, message = save_to_google_sheets(
        category=category,
        concept=concept,
        code_example=st.session_state.editor_text,
        output_text=output_text,
        explanation=explanation,
        notes=notes,
    )

    if success:
        st.success(message)
    else:
        st.error(message)
