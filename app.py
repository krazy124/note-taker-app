import io
import csv
import json
import contextlib

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

if "separated_text" not in st.session_state:
    st.session_state.separated_text = ""


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

    for i, ex in enumerate(st.session_state.examples, start=1):
        stdout_buffer = io.StringIO()
        result = ""

        if ex["setup"]:
            active_setup = ex["setup"]
            block += "# Setup:\n"
            block += active_setup + "\n\n"

            try:
                exec(active_setup, runtime_env)
            except Exception as e:
                result = f"Error: {e}"

        if not result:
            try:
                with contextlib.redirect_stdout(stdout_buffer):
                    exec(ex["code"], runtime_env)

                result = stdout_buffer.getvalue().strip()

                if result == "":
                    result = "No result"

            except Exception as e:
                result = f"Error: {e}"

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
            i,
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
        rows_to_save = []

        for ex_row in st.session_state.example_rows:
            rows_to_save.append([
                section_id,
                ex_row[0],  # Section Order
                ex_row[1],  # Topic
                ex_row[2],  # Concept
                ex_row[3],  # Instruction
                ex_row[4],  # Code
                ex_row[5],  # Result
                ex_row[6],  # Notes
            ])

        example_sheet.append_rows(rows_to_save)

    return section_id


# =========================
# Separate Existing Block Content
# =========================
def parse_block_content_to_rows(section_id, topic, concept, block_text):
    lines = block_text.splitlines()
    rows = []

    active_setup = ""
    current_example = None
    i = 0

    def finalize_example():
        if current_example is None:
            return

        has_content = (
            current_example["instruction"].strip()
            or current_example["notes"].strip()
            or current_example["result"].strip()
            or "".join(current_example["code_lines"]).strip()
        )

        if not has_content:
            return

        code_only = "\n".join(current_example["code_lines"]).rstrip()

        full_code = ""
        if current_example["setup"].strip():
            full_code += current_example["setup"].strip()

        if current_example["setup"].strip() and code_only.strip():
            full_code += "\n\n"

        if code_only.strip():
            full_code += code_only.strip()

        rows.append([
            section_id,
            len(rows) + 1,
            topic,
            concept,
            current_example["instruction"].strip(),
            full_code.strip(),
            current_example["result"].strip(),
            current_example["notes"].strip(),
        ])

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped == "# Setup:":
            i += 1
            setup_lines = []

            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()

                if next_stripped == "# Setup:" or next_stripped.startswith("# Instruction:"):
                    break

                setup_lines.append(next_line)
                i += 1

            active_setup = "\n".join(setup_lines).strip()
            continue

        if stripped.startswith("# Instruction:"):
            finalize_example()

            current_example = {
                "setup": active_setup,
                "instruction": stripped.replace("# Instruction:", "", 1).strip(),
                "notes": "",
                "code_lines": [],
                "result": "",
            }
            i += 1
            continue

        if stripped.startswith("# Notes:"):
            if current_example is None:
                current_example = {
                    "setup": active_setup,
                    "instruction": "",
                    "notes": "",
                    "code_lines": [],
                    "result": "",
                }

            current_example["notes"] = stripped.replace("# Notes:", "", 1).strip()
            i += 1
            continue

        if stripped.startswith("# Result:"):
            if current_example is None:
                current_example = {
                    "setup": active_setup,
                    "instruction": "",
                    "notes": "",
                    "code_lines": [],
                    "result": "",
                }

            inline_result = stripped.replace("# Result:", "", 1).strip()

            if inline_result:
                current_example["result"] = inline_result
                i += 1
                continue

            i += 1
            result_lines = []

            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()

                if next_stripped == "":
                    if result_lines:
                        break
                    i += 1
                    continue

                if next_stripped == "# Setup:" or next_stripped.startswith("# Instruction:"):
                    break

                if next_stripped.startswith("# "):
                    result_lines.append(next_stripped[2:])
                    i += 1
                    continue

                break

            current_example["result"] = "\n".join(result_lines).strip()
            continue

        if current_example is not None:
            current_example["code_lines"].append(line)

        i += 1

    finalize_example()
    return rows


def rows_to_tsv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue()


# =========================
# App UI
# =========================
st.title("Python Review Block Builder")

tab1, tab2 = st.tabs(["Build Review Block", "Separate Existing Block"])


with tab1:
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


with tab2:
    st.subheader("Separate Existing Block Content")

    separate_section_id = st.text_input("Section ID", key="separate_section_id")
    separate_topic = st.text_input("Topic", key="separate_topic")
    separate_concept = st.text_input("Concept", key="separate_concept")

    block_content_input = st.text_area(
        "Block Content",
        height=350,
        key="block_content_input"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Separate", key="separate_button"):
            separated_rows = parse_block_content_to_rows(
                section_id=separate_section_id,
                topic=separate_topic,
                concept=separate_concept,
                block_text=block_content_input
            )

            st.session_state.separated_text = rows_to_tsv(separated_rows)

    with col2:
        st.components.v1.html(
            f"""
            <div style="display:flex; flex-direction:column; gap:8px;">
                <button
                    id="copy-btn"
                    style="
                        width: 100%;
                        padding: 0.6rem 1rem;
                        border: 1px solid #666;
                        border-radius: 0.5rem;
                        background: #f5f5f5;
                        cursor: pointer;
                        font-size: 1rem;
                    "
                >
                    Copy Separated
                </button>

                <div id="copy-status" style="font-size:0.9rem; color:#4CAF50;"></div>
            </div>

            <script>
            const textToCopy = {json.dumps(st.session_state.separated_text)};

            document.getElementById("copy-btn").addEventListener("click", async function() {{
                const status = document.getElementById("copy-status");

                try {{
                    await navigator.clipboard.writeText(textToCopy);
                    status.innerText = "Copied!";
                }} catch (err) {{
                    try {{
                        const temp = document.createElement("textarea");
                        temp.value = textToCopy;
                        document.body.appendChild(temp);
                        temp.select();
                        document.execCommand("copy");
                        document.body.removeChild(temp);
                        status.innerText = "Copied!";
                    }} catch (err2) {{
                        status.innerText = "Copy failed";
                    }}
                }}
            }});
            </script>
            """,
            height=80,
        )

    st.text_area(
        "Separated",
        st.session_state.separated_text,
        height=350
    )
