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

    last = values[-1]

    try:
        num = int(last.replace("s", ""))
        return f"s{num+1}"
    except:
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
            "code": "",
            "result": ""
        }
    ]


if "compiled_block" not in st.session_state:
    st.session_state.compiled_block = ""


def add_example():

    st.session_state.examples.append(
        {
            "setup": "",
            "instruction": "",
            "notes": "",
            "code": "",
            "result": ""
        }
    )


# =========================
# Compile Block
# =========================
def compile_block(section_name, concept):

    block = ""

    block += f"# Section: {section_name}\n"
    block += f"# Concept: {concept}\n\n"

    for ex in st.session_state.examples:

        if ex["setup"]:
            block += "# Setup:\n"
            block += ex["setup"] + "\n\n"

        if ex["instruction"]:
            block += "# Instruction:\n"
            block += ex["instruction"] + "\n\n"

        if ex["notes"]:
            block += "# Notes:\n"
            block += ex["notes"] + "\n\n"

        if ex["code"]:
            block += ex["code"] + "\n\n"

        if ex["result"]:
            block += "# Result:\n"
            block += ex["result"] + "\n\n"

    st.session_state.compiled_block = block


# =========================
# Run Code
# =========================
def run_examples():

    for ex in st.session_state.examples:

        stdout_buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_buffer):
                exec(ex["code"], {})

            ex["result"] = stdout_buffer.getvalue()

        except Exception:
            ex["result"] = traceback.format_exc()


# =========================
# Save to Google Sheets
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
# Section Info
# =========================
st.subheader("Section Information")

section_name = st.text_input("Section Name")

concept = st.text_input("Concept")


# =========================
# Example Forms
# =========================
st.subheader("Example Entries")

for i, ex in enumerate(st.session_state.examples):

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

    ex["code"] = st_ace(
        value=ex["code"],
        language="python",
        theme="monokai",
        key=f"code_{i}",
        height=250
    )

    ex["result"] = st.text_area(
        "Result",
        value=ex["result"],
        key=f"result_{i}"
    )


st.button("Insert Another Example", on_click=add_example)


# =========================
# Controls
# =========================
col1, col2 = st.columns(2)

with col1:
    st.button("Run Code", on_click=run_examples)

with col2:
    st.button("Compile Block", on_click=lambda: compile_block(section_name, concept))


# =========================
# Preview Block
# =========================
st.subheader("Compiled Block Preview")

st.code(st.session_state.compiled_block, language="python")


# =========================
# Save
# =========================
if st.button("Save to Google Sheets", use_container_width=True):

    if not section_name:
        st.error("Section Name required")
    else:

        section_id = save_block(section_name, concept)

        st.success(f"Saved as {section_id}")
