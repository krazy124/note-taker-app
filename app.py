import io
import csv
import json
import contextlib
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
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


def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


# =========================
# Voice Helpers
# =========================
def render_voice_component(component_key):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <script src="https://unpkg.com/streamlit-component-lib@1.4.0/dist/index.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                background: transparent;
            }}

            .voice-wrap {{
                border: 1px solid #d0d0d0;
                border-radius: 12px;
                padding: 12px;
                background: #fafafa;
            }}

            .voice-row {{
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                margin-bottom: 10px;
            }}

            button {{
                border: 1px solid #666;
                background: white;
                border-radius: 10px;
                padding: 10px 14px;
                cursor: pointer;
                font-weight: 600;
                font-size: 14px;
            }}

            button:hover {{
                background: #f1f1f1;
            }}

            .status {{
                font-size: 14px;
                margin-bottom: 8px;
                font-weight: 600;
            }}

            .status.listening {{
                color: #0a7d1c;
            }}

            .status.idle {{
                color: #666;
            }}

            .status.error {{
                color: #b42318;
            }}

            textarea {{
                width: 100%;
                min-height: 140px;
                resize: vertical;
                border-radius: 10px;
                border: 1px solid #c8c8c8;
                padding: 10px;
                font-size: 15px;
                box-sizing: border-box;
                font-family: Arial, sans-serif;
            }}

            .small {{
                margin-top: 8px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="voice-wrap">
            <div id="status" class="status idle">Status: Idle</div>

            <div class="voice-row">
                <button id="startBtn">Start Listening</button>
                <button id="stopBtn">Stop Listening</button>
                <button id="clearBtn">Clear Transcript</button>
            </div>

            <textarea id="transcriptBox" placeholder="Voice transcript will appear here..."></textarea>

            <div class="small">
                Uses your browser's built-in speech recognition. Best for Phase 1 plain dictation.
            </div>
        </div>

        <script>
            const transcriptBox = document.getElementById("transcriptBox");
            const statusEl = document.getElementById("status");
            const startBtn = document.getElementById("startBtn");
            const stopBtn = document.getElementById("stopBtn");
            const clearBtn = document.getElementById("clearBtn");

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            let recognition = null;
            let finalTranscript = "";
            let interimTranscript = "";
            let isListening = false;
            let lastError = "";

            function sendValue() {{
                Streamlit.setComponentValue({{
                    transcript: finalTranscript,
                    interim: interimTranscript,
                    is_listening: isListening,
                    supported: !!SpeechRecognition,
                    error: lastError,
                    ts: Date.now()
                }});
            }}

            function setStatus(text, cls) {{
                statusEl.textContent = text;
                statusEl.className = "status " + cls;
            }}

            function refreshBox() {{
                const combined = [finalTranscript, interimTranscript].filter(Boolean).join(" ").trim();
                transcriptBox.value = combined;
            }}

            function syncTypedBoxToFinal() {{
                finalTranscript = transcriptBox.value;
                interimTranscript = "";
                sendValue();
            }}

            transcriptBox.addEventListener("input", syncTypedBoxToFinal);

            function init() {{
                Streamlit.setFrameHeight(260);

                if (!SpeechRecognition) {{
                    setStatus("Status: Speech recognition not supported in this browser", "error");
                    sendValue();
                    return;
                }}

                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = "en-US";

                recognition.onstart = function() {{
                    isListening = true;
                    lastError = "";
                    setStatus("Status: Listening...", "listening");
                    sendValue();
                }};

                recognition.onresult = function(event) {{
                    interimTranscript = "";

                    for (let i = event.resultIndex; i < event.results.length; i++) {{
                        const chunk = event.results[i][0].transcript.trim();

                        if (event.results[i].isFinal) {{
                            finalTranscript = (finalTranscript + " " + chunk).trim();
                        }} else {{
                            interimTranscript = (interimTranscript + " " + chunk).trim();
                        }}
                    }}

                    refreshBox();
                    sendValue();
                }};

                recognition.onerror = function(event) {{
                    lastError = event.error || "unknown_error";
                    isListening = false;
                    setStatus("Status: Error - " + lastError, "error");
                    sendValue();
                }};

                recognition.onend = function() {{
                    isListening = false;
                    interimTranscript = "";
                    refreshBox();
                    setStatus("Status: Idle", "idle");
                    sendValue();
                }};

                startBtn.addEventListener("click", function() {{
                    try {{
                        recognition.start();
                    }} catch (err) {{}}
                }});

                stopBtn.addEventListener("click", function() {{
                    try {{
                        recognition.stop();
                    }} catch (err) {{}}
                }});

                clearBtn.addEventListener("click", function() {{
                    finalTranscript = "";
                    interimTranscript = "";
                    lastError = "";
                    refreshBox();
                    setStatus("Status: Idle", "idle");
                    sendValue();
                }});

                sendValue();
            }}

            function onRender(event) {{
                init();
            }}

            Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
            Streamlit.setComponentReady();
            Streamlit.setFrameHeight(260);
        </script>
    </body>
    </html>
    """
    return components.html(html, height=260, key=component_key)


def append_text(existing_text, incoming_text):
    existing_text = str(existing_text or "")
    incoming_text = str(incoming_text or "").strip()

    if not incoming_text:
        return existing_text

    if not existing_text.strip():
        return incoming_text

    return existing_text.rstrip() + "\n" + incoming_text


def replace_text(existing_text, incoming_text):
    return str(incoming_text or "").strip()


def apply_voice_text_to_target(example_index, target_field, mode):
    transcript = st.session_state.voice_transcript.strip()

    if not transcript:
        st.warning("No voice transcript to insert.")
        return

    ex = st.session_state.examples[example_index]

    if target_field not in ["instruction", "notes", "setup", "code"]:
        st.error("Invalid target field.")
        return

    current_value = ex.get(target_field, "")

    if mode == "append":
        ex[target_field] = append_text(current_value, transcript)
    elif mode == "replace":
        ex[target_field] = replace_text(current_value, transcript)

    st.session_state.examples[example_index] = ex

    if target_field == "code":
        st.session_state.ace_refresh_token += 1

    safe_rerun()


# =========================
# Build Review Viewer Text
# =========================
def build_review_view_text(section_rows, show_setup, show_instruction, show_notes, show_code, show_result):
    lines = []

    for index, row in enumerate(section_rows):
        setup_text = str(row.get("Setup", "")).replace("\r\n", "\n").replace("\r", "\n").strip()
        code_text = str(row.get("Code", "")).replace("\r\n", "\n").replace("\r", "\n").strip()
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
            "code": ""
        }
    ]

if "compiled_block" not in st.session_state:
    st.session_state.compiled_block = ""

if "example_rows" not in st.session_state:
    st.session_state.example_rows = []

if "separated_text" not in st.session_state:
    st.session_state.separated_text = ""

if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""

if "voice_interim" not in st.session_state:
    st.session_state.voice_interim = ""

if "voice_supported" not in st.session_state:
    st.session_state.voice_supported = None

if "voice_error" not in st.session_state:
    st.session_state.voice_error = ""

if "voice_is_listening" not in st.session_state:
    st.session_state.voice_is_listening = False

if "voice_target_example" not in st.session_state:
    st.session_state.voice_target_example = 0

if "voice_target_field" not in st.session_state:
    st.session_state.voice_target_field = "code"

if "ace_refresh_token" not in st.session_state:
    st.session_state.ace_refresh_token = 0


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
    example_rows = []

    for i, ex in enumerate(st.session_state.examples, start=1):
        stdout_buffer = io.StringIO()
        result = ""
        current_setup = ex["setup"].strip()
        current_code = ex["code"].strip()
        runtime_env = {}

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
                ex_row[6],  # Result
                ex_row[7],  # Notes
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
            "result": "",
        }

    def finalize_example():
        if current_example is None:
            return

        code_only = "\n".join(current_example["code_lines"]).rstrip()

        has_content = (
            current_example["setup"].strip()
            or current_example["instruction"].strip()
            or current_example["notes"].strip()
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
st.markdown(
    '<div class="small-muted">Spreadsheet-style layout, but friendlier to code and mobile screens.</div>',
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["Build Review Block", "Separate Existing Block", "Review Viewer"])


with tab1:
    st.subheader("Section Information")

    top_col1, top_col2 = st.columns(2)

    with top_col1:
        section_name = st.text_input("Section Name")

    with top_col2:
        concept = st.text_input("Concept")

    st.markdown("---")

    st.subheader("Voice Input - Phase 1")
    st.caption("Plain dictation first. Capture voice, then insert it into the field you want.")

    voice_control_col1, voice_control_col2 = st.columns(2)

    with voice_control_col1:
        example_labels = [f"Example {i+1}" for i in range(len(st.session_state.examples))]
        selected_example_label = st.selectbox(
            "Voice Target Example",
            options=example_labels,
            index=min(st.session_state.voice_target_example, len(example_labels) - 1) if example_labels else 0
        )
        st.session_state.voice_target_example = example_labels.index(selected_example_label)

    with voice_control_col2:
        field_map = {
            "Instruction": "instruction",
            "Notes": "notes",
            "Setup": "setup",
            "Code": "code",
        }

        selected_field_label = st.selectbox(
            "Voice Target Field",
            options=list(field_map.keys()),
            index=list(field_map.values()).index(st.session_state.voice_target_field)
            if st.session_state.voice_target_field in field_map.values()
            else 3
        )
        st.session_state.voice_target_field = field_map[selected_field_label]

    voice_payload = render_voice_component("voice_phase1_component")

    if isinstance(voice_payload, dict):
        st.session_state.voice_transcript = str(voice_payload.get("transcript", "") or "")
        st.session_state.voice_interim = str(voice_payload.get("interim", "") or "")
        st.session_state.voice_supported = voice_payload.get("supported")
        st.session_state.voice_error = str(voice_payload.get("error", "") or "")
        st.session_state.voice_is_listening = bool(voice_payload.get("is_listening", False))

    voice_status_col1, voice_status_col2 = st.columns(2)

    with voice_status_col1:
        st.text_area(
            "Voice Transcript",
            value=st.session_state.voice_transcript,
            height=140,
            key="voice_transcript_display"
        )

    with voice_status_col2:
        status_lines = []
        status_lines.append(f"Supported: {st.session_state.voice_supported}")
        status_lines.append(f"Listening: {st.session_state.voice_is_listening}")
        status_lines.append(f"Error: {st.session_state.voice_error or 'None'}")
        status_lines.append(f"Target Example: Example {st.session_state.voice_target_example + 1}")
        status_lines.append(f"Target Field: {st.session_state.voice_target_field}")

        st.text_area(
            "Voice Status",
            value="\n".join(status_lines),
            height=140,
            key="voice_status_display"
        )

    voice_action_col1, voice_action_col2, voice_action_col3 = st.columns(3)

    with voice_action_col1:
        if st.button("Append Transcript to Target", use_container_width=True):
            apply_voice_text_to_target(
                example_index=st.session_state.voice_target_example,
                target_field=st.session_state.voice_target_field,
                mode="append"
            )

    with voice_action_col2:
        if st.button("Replace Target with Transcript", use_container_width=True):
            apply_voice_text_to_target(
                example_index=st.session_state.voice_target_example,
                target_field=st.session_state.voice_target_field,
                mode="replace"
            )

    with voice_action_col3:
        if st.button("Clear Saved Transcript", use_container_width=True):
            st.session_state.voice_transcript = ""
            st.session_state.voice_interim = ""
            safe_rerun()

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

            ex["setup"] = st.text_area(
                "Setup",
                value=ex["setup"],
                key=f"setup_{i}",
                height=140
            )

            code_value = st_ace(
                value=ex["code"],
                language="python",
                theme="monokai",
                key=f"code_{i}_{st.session_state.ace_refresh_token}",
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
                    show_result=show_result
                )

                if section_text:
                    combined_lines.append(section_text)

            review_text = "\n".join(combined_lines).strip()

            st.code(review_text, language="python")

    except Exception as e:
        st.error(f"Error loading review viewer: {e}")
