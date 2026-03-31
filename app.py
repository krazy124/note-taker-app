import io
import csv
import json
import contextlib
from datetime import datetime

import streamlit as st
from streamlit_ace import st_ace
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="Python Review Block Builder", layout="wide")


# =========================
# Custom Styling
# =========================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1200px;
    }

    h1, h2, h3 {
        margin-bottom: 0.35rem;
    }

    div[data-testid="stTextInput"] label,
    div[data-testid="stTextArea"] label,
    div[data-testid="stSelectbox"] label {
        font-weight: 600;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        border-radius: 10px;
        padding-top: 0.65rem;
        padding-bottom: 0.65rem;
        font-weight: 600;
    }

    div[data-testid="stCodeBlock"] {
        border-radius: 12px;
    }

    .example-card-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 0.25rem;
        margin-bottom: 0.6rem;
    }

    .small-muted {
        color: #888;
        font-size: 0.92rem;
        margin-top: -0.15rem;
        margin-bottom: 0.75rem;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.7rem;
            padding-right: 0.7rem;
            padding-top: 0.8rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def connect_to_example_sheet():
    spreadsheet = connect_to_spreadsheet()
    return spreadsheet.worksheet("Example View")


# =========================
# Section ID Generator
# =========================
def get_next_section_id():
    worksheet = connect_to_example_sheet()
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


def section_sort_key(section_id):
    sid = str(section_id).strip().lower()
    if sid.startswith("s") and sid[1:].isdigit():
        return int(sid[1:])
    return 999999


def row_matches_search(record, search_text, search_mode):
    if not search_text.strip():
        return True

    search_value = search_text.strip().lower()

    searchable_fields = {
        "Section ID": clean_label_text(record.get("Section ID", "")),
        "Topic": clean_label_text(record.get("Topic", "")),
        "Concept": clean_label_text(record.get("Concept", "")),
        "Instruction": str(record.get("Instruction", "")).strip(),
        "Setup": str(record.get("Setup", "")).strip(),
        "Code": str(record.get("Code", "")).strip(),
        "Mock Input": str(record.get("Mock Input", "")).strip(),
        "Result": str(record.get("Result", "")).strip(),
        "Notes": str(record.get("Notes", "")).strip(),
        "Created At": str(record.get("Created At", "")).strip(),
    }

    if search_mode == "Anywhere":
        combined_text = " ".join(searchable_fields.values()).lower()
        return search_value in combined_text

    field_value = searchable_fields.get(search_mode, "")
    return search_value in field_value.lower()


def get_example_sections(search_text="", search_mode="Anywhere"):
    worksheet = connect_to_example_sheet()
    records = worksheet.get_all_records()

    grouped = {}

    for record in records:
        if not row_matches_search(record, search_text, search_mode):
            continue

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


def build_mock_input_function(mock_input_text):
    normalized = str(mock_input_text).replace("\r\n", "\n").replace("\r", "\n")

    if not normalized.strip():
        def no_mock_input(prompt=""):
            raise RuntimeError("This example uses input(), but no Mock Input was provided.")
        return no_mock_input

    provided_inputs = normalized.split("\n")
    input_index = {"value": 0}

    def mock_input(prompt=""):
        if input_index["value"] >= len(provided_inputs):
            raise RuntimeError("This example requested more input() values than were provided in Mock Input.")
        value = provided_inputs[input_index["value"]]
        input_index["value"] += 1
        return value

    return mock_input


# =========================
# Build Review Viewer Text
# =========================
def build_review_view_text(
    section_rows,
    show_setup,
    show_instruction,
    show_notes,
    show_code,
    show_mock_input,
    show_result
):
    lines = []

    for index, row in enumerate(section_rows):
        setup_text = str(row.get("Setup", "")).replace("\r\n", "\n").replace("\r", "\n").strip()
        code_text = str(row.get("Code", "")).replace("\r\n", "\n").replace("\r", "\n").strip()
        mock_input_text = str(row.get("Mock Input", "")).replace("\r\n", "\n").replace("\r", "\n").strip()
        instruction = str(row.get("Instruction", "")).strip()
        notes = str(row.get("Notes", "")).strip()
        result = str(row.get("Result", "")).strip()

        if show_setup and setup_text:
            lines.append("# Setup:")
            lines.append(setup_text)
            lines.append("")

        if show_instruction and instruction:
            lines.append(f"# Instruction: {instruction}")

        if show_notes and notes:
            lines.append(f"# Notes: {notes}")

        if show_code and code_text:
            lines.append(code_text)

        if show_mock_input and mock_input_text:
            lines.append("# Mock Input:")
            for input_line in mock_input_text.splitlines():
                lines.append(f"# {input_line}")

        if show_result and result:
            if "\n" in result:
                lines.append("# Result:")
                for result_line in result.splitlines():
                    lines.append(f"# {result_line}")
            else:
                lines.append(f"# Result: {result}")

        if index < len(section_rows) - 1:
            lines.append("__________________________________________________")
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
            "code": "",
            "mock_input": ""
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
            "code": "",
            "mock_input": ""
        }
    )


# =========================
# Compile Block
# =========================
def compile_block(section_name, concept):
    block = ""
    example_rows = []

    for i, ex in enumerate(st.session_state.examples, start=1):
        stdout_buffer = io.StringIO()
        result = ""
        current_setup = ex["setup"].strip()
        current_code = ex["code"].strip()
        current_mock_input = ex["mock_input"].replace("\r\n", "\n").replace("\r", "\n").strip()

        runtime_env = {
            "input": build_mock_input_function(ex["mock_input"])
        }

        if current_setup:
            block += "# Setup:\n"
            block += current_setup + "\n\n"

        try:
            if current_setup:
                exec(current_setup, runtime_env)
        except Exception as e:
            result = f"Setup Error: {e}"

        if not result:
            try:
                with contextlib.redirect_stdout(stdout_buffer):
                    exec(current_code, runtime_env)

                result = stdout_buffer.getvalue().strip()

                if result == "":
                    result = "No result"

            except Exception as e:
                result = f"Code Error: {e}"

        if ex["instruction"]:
            block += f"# Instruction: {ex['instruction']}\n"

        if ex["notes"]:
            block += f"# Notes: {ex['notes']}\n"

        if current_code:
            block += current_code + "\n"

        if current_mock_input:
            block += "# Mock Input:\n"
            for input_line in current_mock_input.splitlines():
                block += f"# {input_line}\n"

        if result:
            single_line_result = result.replace("\n", " | ")
            block += f"# Result: {single_line_result}\n"

        block += "\n"

        example_rows.append([
            i,                    # Section Order
            section_name,         # Topic
            concept,              # Concept
            ex["instruction"],    # Instruction
            current_setup,        # Setup
            current_code,         # Code
            current_mock_input,   # Mock Input
            result,               # Result
            ex["notes"]           # Notes
        ])

    st.session_state.compiled_block = block
    st.session_state.example_rows = example_rows


# =========================
# Save Examples Only
# =========================
def save_block_and_examples(section_name, concept):
    example_sheet = connect_to_example_sheet()

    section_id = get_next_section_id()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if st.session_state.example_rows:
        rows_to_save = []

        for ex_row in st.session_state.example_rows:
            rows_to_save.append([
                section_id,
                ex_row[0],  # Section Order
                ex_row[1],  # Topic
                ex_row[2],  # Concept
                ex_row[3],  # Instruction
                ex_row[4],  # Setup
                ex_row[5],  # Code
                ex_row[6],  # Mock Input
                ex_row[7],  # Result
                ex_row[8],  # Notes
                created_at, # Created At
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
            "mock_input_lines": [],
            "result": "",
        }

    def finalize_example():
        if current_example is None:
            return

        code_only = "\n".join(current_example["code_lines"]).rstrip()
        mock_input_only = "\n".join(current_example["mock_input_lines"]).rstrip()

        has_content = (
            current_example["setup"].strip()
            or current_example["instruction"].strip()
            or current_example["notes"].strip()
            or mock_input_only.strip()
            or current_example["result"].strip()
            or code_only.strip()
        )

        if not has_content:
            return

        rows.append([
            str(section_id).strip(),
            len(rows) + 1,
            topic,
            concept,
            current_example["instruction"].strip(),
            current_example["setup"].strip(),
            code_only.strip(),
            mock_input_only.strip(),
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
                    or next_stripped == "# Mock Input:"
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

        if stripped == "# Mock Input:":
            if current_example is None:
                current_example = new_example()

            i += 1
            mock_input_lines = []

            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()

                if not next_stripped:
                    i += 1
                    continue

                if (
                    next_stripped == "# Setup:"
                    or next_stripped == "# Mock Input:"
                    or next_stripped.startswith("# Instruction:")
                    or next_stripped.startswith("# Notes:")
                    or next_stripped.startswith("# Result:")
                ):
                    break

                if next_stripped.startswith("# "):
                    mock_input_lines.append(next_stripped[2:].rstrip())
                    i += 1
                    continue

                break

            current_example["mock_input_lines"] = mock_input_lines
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
                    or next_stripped == "# Mock Input:"
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
st.markdown('<div class="small-muted">Spreadsheet-style layout, but friendlier to code and mobile screens.</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Build Review Block", "Separate Existing Block", "Review Viewer"])


with tab1:
    st.subheader("Section Information")

    top_col1, top_col2 = st.columns(2)

    with top_col1:
        section_name = st.text_input("Section Name")

    with top_col2:
        concept = st.text_input("Concept")

    st.markdown("---")

    for i in range(len(st.session_state.examples)):
        ex = st.session_state.examples[i]

        with st.container(border=True):
            st.markdown(
                f'<div class="example-card-title">Example {i+1}</div>',
                unsafe_allow_html=True
            )

            row1_col1, row1_col2 = st.columns(2)

            with row1_col1:
                ex["instruction"] = st.text_area(
                    "Instruction",
                    value=ex["instruction"],
                    key=f"instruction_{i}",
                    height=120
                )

            with row1_col2:
                ex["notes"] = st.text_area(
                    "Notes",
                    value=ex["notes"],
                    key=f"notes_{i}",
                    height=120
                )

            row2_col1, row2_col2 = st.columns(2)

            with row2_col1:
                ex["setup"] = st.text_area(
                    "Setup",
                    value=ex["setup"],
                    key=f"setup_{i}",
                    height=140
                )

            with row2_col2:
                ex["mock_input"] = st.text_area(
                    "Mock Input (Optional)",
                    value=ex["mock_input"],
                    key=f"mock_input_{i}",
                    height=140,
                    help="Optional. Enter one input per line for code that uses input()."
                )

            code_value = st_ace(
                value=ex["code"],
                language="python",
                theme="monokai",
                key=f"code_{i}",
                height=260
            )

            ex["code"] = code_value if code_value else ""

            st.markdown("")

    action_col1, action_col2 = st.columns([1, 1])

    with action_col1:
        st.button("Insert Another Example", on_click=add_example, use_container_width=True)

    with action_col2:
        if st.button("Compile Block", use_container_width=True):
            compile_block(section_name, concept)

    st.markdown("---")
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

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        separate_section_id = st.text_input("Section ID", key="separate_section_id")
        separate_topic = st.text_input("Topic", key="separate_topic")

    with info_col2:
        separate_concept = st.text_input("Concept", key="separate_concept")

    block_content_input = st.text_area(
        "Block Content",
        height=350,
        key="block_content_input"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Separate", key="separate_button", use_container_width=True):
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
                        padding: 0.7rem 1rem;
                        border: 1px solid #666;
                        border-radius: 0.6rem;
                        background: #f5f5f5;
                        cursor: pointer;
                        font-size: 1rem;
                        font-weight: 600;
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
            height=85,
        )

    st.text_area(
        "Separated",
        st.session_state.separated_text,
        height=350
    )


with tab3:
    st.subheader("Review Viewer")

    try:
        with st.sidebar:
            st.subheader("Review Viewer Controls")

            search_text = st.text_input("Search Text", value="")

            search_mode = st.selectbox(
                "Search In",
                options=[
                    "Anywhere",
                    "Section ID",
                    "Topic",
                    "Concept",
                    "Instruction",
                    "Setup",
                    "Code",
                    "Mock Input",
                    "Result",
                    "Notes",
                    "Created At",
                ],
                index=0
            )

            section_ids, grouped_sections = get_example_sections(
                search_text=search_text,
                search_mode=search_mode
            )

            if section_ids:
                selected_section_id = st.selectbox(
                    "Select Section ID",
                    options=["All Sections"] + section_ids,
                    format_func=lambda sid: "All Sections" if sid == "All Sections" else f"{sid} - {grouped_sections[sid]['topic']} - {grouped_sections[sid]['concept']}"
                )
            else:
                selected_section_id = "All Sections"

            show_headers = st.checkbox("Headers", value=True)
            show_setup = st.checkbox("Setup", value=True)
            show_instruction = st.checkbox("Instruction", value=True)
            show_notes = st.checkbox("Notes", value=True)
            show_code = st.checkbox("Code", value=True)
            show_mock_input = st.checkbox("Mock Input", value=True)
            show_result = st.checkbox("Result", value=True)

        if not section_ids:
            st.info("No Example View rows found for the current search.")
        else:
            if selected_section_id == "All Sections":
                st.markdown("### All Sections")
                st.caption(f"Total Sections: {len(section_ids)}")
            else:
                selected_group = grouped_sections[selected_section_id]
                st.markdown(f"### {selected_group['topic']} - {selected_group['concept']}")
                st.caption(f"Section ID: {selected_section_id}")

            combined_lines = []

            if selected_section_id == "All Sections":
                for sid in section_ids:
                    group = grouped_sections[sid]
                    rows = get_sorted_section_rows(group["rows"])

                    combined_lines.append("__________________________________________________")
                    combined_lines.append("")

                    if show_headers:
                        combined_lines.append(f"# ===== {sid} | {group['topic']} - {group['concept']} =====")
                        combined_lines.append("")

                    section_text = build_review_view_text(
                        section_rows=rows,
                        show_setup=show_setup,
                        show_instruction=show_instruction,
                        show_notes=show_notes,
                        show_code=show_code,
                        show_mock_input=show_mock_input,
                        show_result=show_result
                    )

                    if section_text:
                        combined_lines.append(section_text)
                        combined_lines.append("")
            else:
                group = grouped_sections[selected_section_id]
                rows = get_sorted_section_rows(group["rows"])

                combined_lines.append("__________________________________________________")
                combined_lines.append("")

                if show_headers:
                    combined_lines.append(f"# ===== {selected_section_id} | {group['topic']} - {group['concept']} =====")
                    combined_lines.append("")

                section_text = build_review_view_text(
                    section_rows=rows,
                    show_setup=show_setup,
                    show_instruction=show_instruction,
                    show_notes=show_notes,
                    show_code=show_code,
                    show_mock_input=show_mock_input,
                    show_result=show_result
                )

                if section_text:
                    combined_lines.append(section_text)

            review_text = "\n".join(combined_lines).strip()

            st.code(review_text, language="python")

    except Exception as e:
        st.error(f"Error loading review viewer: {e}")
