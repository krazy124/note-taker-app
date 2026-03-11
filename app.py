import io
import contextlib
import traceback
import textwrap

import streamlit as st
from streamlit_ace import st_ace
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Python Notes Code Editor", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.4rem;
        padding-bottom: 0rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.35rem;
    }

    h1 {
        font-size: 1.8rem !important;
        margin-bottom: 0.2rem !important;
    }

    h2, h3 {
        margin-top: 0.35rem !important;
        margin-bottom: 0.2rem !important;
    }

    p {
        margin-bottom: 0.2rem !important;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.2rem;
            padding-left: 0.35rem;
            padding-right: 0.35rem;
        }

        h1 {
            font-size: 1.4rem !important;
        }

        h2, h3 {
            font-size: 1.15rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


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

    sheet = client.open_by_key("14pnlZ5jfXNC-AGrSsRQAmUQ17Acbn5xxDZQMsAlJQlo")
    worksheet = sheet.sheet1

    return worksheet


# =========================
# Text Formatting Helpers
# =========================
def wrap_text_for_sheet(text, width):
    if not text or not text.strip():
        return ""

    paragraphs = text.splitlines()
    wrapped_paragraphs = []

    for paragraph in paragraphs:
        if not paragraph.strip():
            wrapped_paragraphs.append("")
        else:
            wrapped_paragraphs.append(
                textwrap.fill(paragraph.strip(), width=width)
            )

    return "\n".join(wrapped_paragraphs)


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


def save_to_google_sheets(category, concept, code_example, output_text, explanation, notes, wrap_width):
    try:
        worksheet = connect_to_sheet()

        wrapped_explanation = wrap_text_for_sheet(explanation, wrap_width)
        wrapped_notes = wrap_text_for_sheet(notes, wrap_width)

        new_row = [
            category,
            concept,
            code_example,
            output_text,
            wrapped_explanation,
            wrapped_notes
        ]

        worksheet.append_row(new_row)
        return True, "Saved to Google Sheets!"
    except Exception as e:
        return False, f"Error saving to Google Sheets: {e}"


# =========================
# App UI
# =========================
st.title("Python Notes Editor")


# =========================
# Note Fields
# =========================
st.subheader("Note Entry")

category = st.text_input("Category")
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
    height=420,
    font_size=15,
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
    st.button("Run Code", on_click=run_code, use_container_width=True)

with col2:
    st.button("Clear Console", on_click=clear_console, use_container_width=True)

with col3:
    st.download_button(
        label="Download Code",
        data=st.session_state.editor_text,
        file_name="example.py",
        mime="text/plain",
        use_container_width=True
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
    height=100
)

wrap_width = st.number_input(
    "Characters before line break for Explanation and Notes",
    min_value=20,
    max_value=200,
    value=60,
    step=5
)

explanation = st.text_area(
    "Explanation",
    height=140
)

notes = st.text_area(
    "Notes",
    height=140
)


# =========================
# Save to Google Sheets
# =========================
if st.button("Save to Google Sheets", use_container_width=True):
    success, message = save_to_google_sheets(
        category=category,
        concept=concept,
        code_example=st.session_state.editor_text,
        output_text=output_text,
        explanation=explanation,
        notes=notes,
        wrap_width=wrap_width,
    )

    if success:
        st.success(message)
    else:
        st.error(message)
