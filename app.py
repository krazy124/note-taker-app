import io
import contextlib
import traceback

import streamlit as st
from streamlit_ace import st_ace

st.set_page_config(page_title="Python Notes Code Editor", layout="wide")

st.title("Python Notes Code Editor")

st.write("Write Python code, run it, and view the output below.")

if "code" not in st.session_state:
    st.session_state.code = """food_temp = 125

if food_temp > 140:
    print("too hot to eat")
elif food_temp > 130:
    print("hot but safe to eat")
elif food_temp > 120:
    print("ideal eating temperature")
else:
    print("food is cold")
"""

if "console_output" not in st.session_state:
    st.session_state.console_output = ""

if "console_error" not in st.session_state:
    st.session_state.console_error = ""

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

col1, col2, col3 = st.columns(3)

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
    st.download_button(
        label="Download Code",
        data=code,
        file_name="example.py",
        mime="text/plain"
    )

st.subheader("Console")

if st.session_state.console_output:
    st.code(st.session_state.console_output, language="text")
else:
    st.code("", language="text")

if st.session_state.console_error:
    st.subheader("Errors")
    st.code(st.session_state.console_error, language="text")

st.subheader("Notes")
notes = st.text_area("Explanation / Notes", height=150)
