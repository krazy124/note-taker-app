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
    worksheet = sheet.worksheet("New Review")

    return worksheet


# =========================
# Section ID Generator
# =========================
def get_next_section_id():

    worksheet = connect_to_sheet()
    values = worksheet.col_values(1)

    if len(values) <= 1:
        return "s1"

    data_rows = values[1:]  # skip header

    for value in reversed(data_rows):
        cleaned = str(value).strip().lower()

        if cleaned.startswith("s") and cleaned[1:].isdigit():
            num = int(cleaned[1:])
            return f"s{num + 1}"

    return "s1"



# =========================
# Example State
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
    runtime_env = {}   # shared environment across examples

    for ex in st.session_state.examples:

        stdout_buffer = io.StringIO()

        # update setup if new one is provided
        if ex["setup"]:
            active_setup = ex["setup"]

            block += "# Setup:\n"
            block += active_setup + "\n\n"

            # run setup once to initialize environment
            exec(active_setup, runtime_env)

        try:

            with contextlib.redirect_stdout(stdout_buffer):
                exec(ex["code"], runtime_env)

            result = stdout_buffer.getvalue().strip()

        except Exception:
            result = traceback.format_exc()

        if ex["instruction"]:
            block += f"# Instruction: {ex['instruction']}\n"

        if ex["notes"]:
            block += f"# Notes: {ex['notes']}\n"

        block += ex["code"] + "\n"

        if result:
            block += f"# Result: {result}\n"

        block += "\n"

    st.session_state.compiled_block = block




# =========================
# Save Block
# =========================
def save_block(section_name, concept):

    worksheet = connect_to_sheet()

    section_id = get_next_section_id()

    new_row = [
        section_id,
        section_name,
        concept,
        st.session_state.compiled_block
    ]

    worksheet.append_row(new_row)

    return section_id


# =========================
# App UI
# =========================
st.title("Python Review Block Builder")


# =========================
# Section Fields
# =========================
st.subheader("Section Information")

section_name = st.text_input("Section Name")

concept = st.text_input("Concept")


# =========================
# Example Forms
# =========================
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


# =========================
# Compile Button
# =========================
st.button(
    "Compile Block",
    on_click=lambda: compile_block(section_name, concept)
)


# =========================
# Preview
# =========================
st.subheader("Compiled Block Preview")

st.code(st.session_state.compiled_block, language="python")


# =========================
# Save
# =========================
if st.button("Save to Google Sheets", use_container_width=True):

    compile_block(section_name, concept)

    if not section_name:
        st.error("Section Name required")
    else:

        section_id = save_block(section_name, concept)

        st.success(f"Saved as {section_id}")
