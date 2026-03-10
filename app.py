import io
import contextlib
import traceback

import streamlit as st
from streamlit_ace import st_ace

st.set_page_config(page_title="Python Notes Code Editor", layout="wide")

st.title("Python Notes Code Editor")
st.write("Write Python code, run it, and view the output below.")

# ----------------------------
# Session state setup
# ----------------------------
if "editor_text" not in st.session_state:
    st.session_state.editor_text = ""

if "console_output" not in st.session_state:
    st.session_state.console_output = ""

if "console_error" not in st.session_state:
    st.session_state.console_error = ""


# ----------------------------
# Button callback functions
# ----------------------------
def clear_editor():
    st.session_state.editor_text = ""


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


# ----------------------------
# Top buttons
# ----------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.button("Run Code", on_click=run_code)

with col2:
    st.button("Clear Console", on_click=clear_console)

with col3:
    st.button("Clear Editor", on_click=clear_editor)

with col4:
    st.download_button(
        label="Download Code",
        data=st.session_state.editor_text,
        file_name="example.py",
        mime="text/plain"
    )

# ----------------------------
# Code editor
# ----------------------------
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

# Sync editor back into session state
st.session_state.editor_text = editor_value

# ----------------------------
# Console
# ----------------------------
st.subheader("Console")
st.code(st.session_state.console_output or "", language="text")

if st.session_state.console_error:
    st.subheader("Errors")
    st.code(st.session_state.console_error, language="text")

# ----------------------------
# Notes
# ----------------------------
st.subheader("Notes")
notes = st.text_area("Explanation / Notes", height=150)
