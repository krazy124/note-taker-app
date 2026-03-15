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
# Helpers
# =========================
def clean_label_text(value):
    text = str(value).strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1]
    return text.strip()


def split_setup_and_code(full_code):
    code_text = str(full_code).replace("\r\n", "\n").replace("\r", "\n").strip()

    if "\n\n" in code_text:
        setup_part, code_part = code_text.split("\n\n", 1)
        return setup_part.strip(), code_part.strip()

    return "", code_text


def section_sort_key(section_id):
    sid = str(section_id).strip().lower()
    if sid.startswith("s") and sid[1:].isdigit():
        return int(sid[1:])
    return 999999


def get_example_sections():
    worksheet = connect_to_example_sheet()
    records = worksheet.get_all_records()

    grouped = {}

    for record in records:
        section_id = clean_label_text(record.get("Section ID", ""))
        topic = clean_label_text(record.get("Topic", ""))
        concept = clean_label_text(record.get("Concept", ""))

        if not section_id:
            continue

        if section_id not in grouped:
            grouped[section_id] = {
                "topic": topic,
                "concept": concept,
                "rows": []
            }

        grouped[section_id]["rows"].append(record)

    ordered_ids = sorted(grouped.keys(), key=section_sort_key)
    return ordered_ids, grouped


def get_sorted_section_rows(section_rows):
    def row_order_key(row):
        raw_order = str(row.get("Section Order", "")).strip()
        return int(raw_order) if raw_order.isdigit() else 999999

    return sorted(section_rows, key=row_order_key)


# =========================
# Build Review Viewer Text
# =========================
def build_review_view_text(section_rows, show_setup, show_instruction, show_notes, show_code, show_result):
    lines = []
    previous_setup = None

    for row in section_rows:
        full_code = str(row.get("Code", "")).replace("\r\n", "\n").replace("\r", "\n").strip()
        instruction = str(row.get("Instruction", "")).strip()
        notes = str(row.get("Notes", "")).strip()
        result = str(row.get("Result", "")).strip()

        setup_text = ""
        code_text = full_code

        if "\n\n" in full_code:
            setup_text, code_text = full_code.split("\n\n", 1)
            setup_text = setup_text.strip()
            code_text = code_text.strip()

        if show_setup and setup_text and setup_text != previous_setup:
            lines.append("# Setup:")
            lines.append(setup_text)
            lines.append("")
            previous_setup = setup_text
        elif setup_text:
            previous_setup = setup_text

        if show_instruction and instruction:
            lines.append(f"# Instruction: {instruction}")

        if show_notes and notes:
            lines.append(f"# Notes: {notes}")

        if show_code and code_text:
            lines.append(code_text)

        if show_result and result:
            if "\n" in result:
                lines.append("# Result:")
                for result_line in result.splitlines():
                    lines.append(f"# {result_line}")
            else:
                lines.append(f"# Result: {result}")

        lines.append("")

    return "\n".join(lines).strip()


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

    topic = str(topic).strip().strip('"')
    concept = str(concept).strip().strip('"')

    active_setup = ""
    current_example = None
    i = 0

    def new_example():
        return {
            "setup": active_setup,
            "instruction": "",
            "notes": "",
            "code_lines": [],
            "result": "",
        }

    def finalize_example():
        if current_example is None:
            return

        code_only = "\n".join(current_example["code_lines"]).rstrip()

        has_content = (
            current_example["instruction"].strip()
            or current_example["notes"].strip()
            or current_example["result"].strip()
            or code_only.strip()
        )

        if not has_content:
            return

        full_code = ""
        if current_example["setup"].strip():
            full_code += current_example["setup"].strip()

        if current_example["setup"].strip() and code_only.strip():
            full_code += "\n\n"

        if code_only.strip():
            full_code += code_only.strip()

        rows.append([
            str(section_id).strip(),
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
                next_stripped = lines[i].strip()

                if (
                    next_stripped == "# Setup:"
                    or next_stripped.startswith("# Instruction:")
                    or next_stripped.startswith("# Notes:")
                    or next_stripped.startswith("# Result:")
                ):
                    break

                setup_lines.append(lines[i])
                i += 1

            active_setup = "\n".join(setup_lines).strip()
            continue

        if stripped.startswith("# Instruction:"):
            finalize_example()
            current_example = new_example()
            current_example["instruction"] = stripped.replace("# Instruction:", "", 1).strip()
            i += 1
            continue

        if stripped.startswith("# Notes:"):
            if current_example is None:
                current_example = new_example()

            current_example["notes"] = stripped.replace("# Notes:", "", 1).strip()
            i += 1
            continue

        if stripped.startswith("# Result:"):
            if current_example is None:
                current_example = new_example()

            result_lines = []
            inline_result = stripped.replace("# Result:", "", 1).strip()

            if inline_result:
                result_lines.append(inline_result)

            i += 1

            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()

                if not next_stripped:
                    i += 1
                    continue

                if (
                    next_stripped == "# Setup:"
                    or next_stripped.startswith("# Instruction:")
                    or next_stripped.startswith("# Notes:")
                    or next_stripped.startswith("# Result:")
                ):
                    break

                if next_stripped.startswith("# "):
                    result_lines.append(next_stripped[2:].rstrip())
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

tab1, tab2, tab3 = st.tabs(["Build Review Block", "Separate Existing Block", "Review Viewer"])


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


with tab3:
    st.subheader("Review Viewer")

    try:
        section_ids, grouped_sections = get_example_sections()

        if not section_ids:
            st.info("No Example View rows found yet.")
        else:
            selected_section_id = st.selectbox(
                "Select Section ID",
                options=section_ids,
                format_func=lambda sid: f"{sid} - {grouped_sections[sid]['topic']} - {grouped_sections[sid]['concept']}"
            )

            selected_group = grouped_sections[selected_section_id]
            selected_rows = get_sorted_section_rows(selected_group["rows"])

            st.markdown(f"### {selected_group['topic']} - {selected_group['concept']}")
            st.caption(f"Section ID: {selected_section_id}")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                show_setup = st.checkbox("Setup", value=True)

            with col2:
                show_instruction = st.checkbox("Instruction", value=True)

            with col3:
                show_notes = st.checkbox("Notes", value=True)

            with col4:
                show_code = st.checkbox("Code", value=True)

            with col5:
                show_result = st.checkbox("Result", value=True)

            review_text = build_review_view_text(
                section_rows=selected_rows,
                show_setup=show_setup,
                show_instruction=show_instruction,
                show_notes=show_notes,
                show_code=show_code,
                show_result=show_result
            )

            st.code(review_text, language="python")

    except Exception as e:
        st.error(f"Error loading review viewer: {e}")
