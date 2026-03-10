import io
import contextlib
import traceback

import streamlit as st
from streamlit_ace import st_ace

st.set_page_config(page_title="Python Notes Code Editor", layout="wide")

st.title("Python Notes Code Editor")

st.write("Write Python code, run it, and view the output below.")

# Initialize session state
if "code" not in st.session_state:
    st.session_state.code = ""

if "console_output" not in st.session_state:
    st.session_state.console_output = ""

if "console_error" not in st.session_state:
    st.session_state.console_error = ""

# Code editor
code = st_ace(
    value=st.session_state.code,
    language="python",
    theme="monokai",
    key="code_editor",
    height=400,
    font_size=14,
    tab_size=4,
    show_gutter=True,
    wrap=True,
    auto_update=True,
)

st.session_state.code = code

# Buttons
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Run Code"):
        stdout_buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_buffer):
                exec(code, {})
            st.session_state.console_output = stdout_buffer.getvalue()
            st.session_state.console_error = ""
        except Exception:
            st.session_state.console_output = stdout_buffer.getvalue()
            st.session_state.console_error = traceback.format_exc()

with col2:
    if st.button("Clear Console"):
        st.session_state.console_output = ""
        st.session_state.console_error = ""

with col3:
    if st.button("Clear Editor"):
        st.session_state.code_editor = ""
        st.rerun()

with col4:
    st.download_button(
        label="Download Code",
        data=code,
        file_name="example.py",
        mime="text/plain"
    )

# Console output
st.subheader("Console")

if st.session_state.console_output:
    st.code(st.session_state.console_output, language="text")
else:
    st.code("", language="text")

if st.session_state.console_error:
    st.subheader("Errors")
    st.code(st.session_state.console_error, language="text")

# Notes
st.subheader("Notes")
notes = st.text_area("Explanation / Notes", height=150)
