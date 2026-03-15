import io
import contextlib
import traceback

import streamlit as st
from streamlit_ace import st_ace
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Python Review Block Builder", layout="wide")


# =========================
# Google Sheets Connection
# =========================
def connect_to_spreadsheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("14pnlZ5jfXNC-AGrSsRQAmUQ17Acbn5xxDZQMsAlJQlo")
    return spreadsheet


def connect_to_review_sheet():
    spreadsheet = connect_to_spreadsheet()
    return spreadsheet.worksheet("New Review")


def connect_to_example_sheet():
    spreadsheet = connect_to_spreadsheet()
    return spreadsheet.worksheet("Example View")


# =========================
# Section ID Generator
# =========================
def get_next_section_id():
    worksheet = connect_to_review_sheet()
    values = worksheet.col_values(1)

    if len(values) <= 1:
        return "s1"

    data_rows = values[1:]

    for value in reversed(data_rows):
        cleaned = str(value).strip().lower()

        if cleaned.startswith("s") and cleaned[1:].isdigit():
            num = int(cleaned[1:])
            return f"s{num + 1}"

    return "s1"


# =========================
# Session State
# =========================
if "examples" not in st.session_state:
    st.session_state.examples = [
        {
            "setup": "",
            "instruction": "",
            "notes": "",
            "code": ""
        }
    ]

if "compiled_block" not in st.session_state:
    st.session_state.compiled_block = ""

if "example_rows" not in st.session_state:
    st.session_state.example_rows = []


# =========================
# Add Example
# =========================
def add_example():
    st.session_state.examples.append(
        {
            "setup": "",
            "instruction": "",
            "notes": "",
            "code": ""
        }
    )


# =========================
# Compile Block
# =========================
def compile_block(section_name, concept):
    block = ""
    active_setup = ""
    runtime_env = {}
    example_rows = []

    for ex in st.session_state.examples:
        stdout_buffer = io.StringIO()
        result = ""

        if ex["setup"]:
            active_setup = ex["setup"]
            block += "# Setup:\n"
            block += active_setup + "\n\n"

            try:
                exec(active_setup, runtime_env)
            except Exception:
                result = traceback.format_exc()

        if not result:
            try:
                with contextlib.redirect_stdout(stdout_buffer):
                    exec(ex["code"], runtime_env)
                
                result = stdout_buffer.getvalue().strip()
                
                # If nothing was printed, treat it as a valid case
                if result == "":
                    result = "No result"
    
                except Exception:
                    result = traceback.format_exc().strip()

        if ex["instruction"]:
            block += f"# Instruction: {ex['instruction']}\n"

        if ex["notes"]:
            block += f"# Notes: {ex['notes']}\n"

        block += ex["code"] + "\n"

        if result:
            single_line_result = result.replace("\n", " | ")
            block += f"# Result: {single_line_result}\n"

        block += "\n"

        code_for_example_view = ""
        if active_setup:
            code_for_example_view += active_setup + "\n\n"
        code_for_example_view += ex["code"]

        example_rows.append([
            section_name,
            concept,
            ex["instruction"],
            code_for_example_view.strip(),
            result,
            ex["notes"]
        ])

    st.session_state.compiled_block = block
    st.session_state.example_rows = example_rows


# =========================
# Save Block + Examples
# =========================
def save_block_and_examples(section_name, concept):
    review_sheet = connect_to_review_sheet()
    example_sheet = connect_to_example_sheet()

    section_id = get_next_section_id()

    review_row = [
        section_id,
        section_name,
        concept,
        st.session_state.compiled_block
    ]

    review_sheet.append_row(review_row)

    if st.session_state.example_rows:
        example_sheet.append_rows(st.session_state.example_rows)

    return section_id


# =========================
# App UI
# =========================
st.title("Python Review Block Builder")

st.subheader("Section Information")
section_name = st.text_input("Section Name")
concept = st.text_input("Concept")

for i in range(len(st.session_state.examples)):
    ex = st.session_state.examples[i]

    st.markdown(f"### Example {i+1}")

    ex["setup"] = st.text_area(
        "Setup",
        value=ex["setup"],
        key=f"setup_{i}"
    )

    ex["instruction"] = st.text_area(
        "Instruction",
        value=ex["instruction"],
        key=f"instruction_{i}"
    )

    ex["notes"] = st.text_area(
        "Notes",
        value=ex["notes"],
        key=f"notes_{i}"
    )

    code_value = st_ace(
        value=ex["code"],
        language="python",
        theme="monokai",
        key=f"code_{i}",
        height=250
    )

    ex["code"] = code_value if code_value else ""

st.button("Insert Another Example", on_click=add_example)

st.button(
    "Compile Block",
    on_click=lambda: compile_block(section_name, concept)
)

st.subheader("Compiled Block Preview")
st.code(st.session_state.compiled_block, language="python")

if st.button("Save to Google Sheets", use_container_width=True):
    compile_block(section_name, concept)

    if not section_name:
        st.error("Section Name required")
    else:
        section_id = save_block_and_examples(section_name, concept)
        st.success(f"Saved as {section_id}")
