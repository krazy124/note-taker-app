import textwrap
import streamlit as st
from streamlit_ace import st_ace


INDENT = "    "  # 4 spaces is the standard Python indent
DEFAULT_CODE = '''food_temp = 125

if food_temp > 140:
    print("too hot to eat")
elif food_temp > 130:
    print("hot but safe to eat")
elif food_temp > 120:
    print("ideal eating temperature")
elif food_temp > 110:
    print("very warm and easy to eat")
elif food_temp > 100:
    print("food is warm but almost too cool")
else:
    print("food is cold")
'''


def normalize_python_indentation(code: str) -> str:
    """Convert tabs to 4 spaces and trim trailing whitespace.

    This does not try to fully auto-fix Python syntax. It just cleans up
    indentation so code is easier to reuse in editors or spreadsheets.
    """
    lines = code.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned = []
    for line in lines:
        line = line.replace("\t", INDENT).rstrip()
        cleaned.append(line)
    return "\n".join(cleaned).strip("\n")


def wrap_notes(text: str, width: int = 60) -> str:
    """Wrap long note text for easier spreadsheet reading."""
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n")]
    wrapped = []
    for p in paragraphs:
        if not p:
            wrapped.append("")
        else:
            wrapped.append(textwrap.fill(p, width=width))
    return "\n".join(wrapped)


st.set_page_config(page_title="Python Notes Code Editor", layout="wide")
st.title("Python Notes Code Editor")
st.caption("A mini Streamlit editor for Python study notes.")

if "code_value" not in st.session_state:
    st.session_state.code_value = DEFAULT_CODE
if "notes_value" not in st.session_state:
    st.session_state.notes_value = "Python checks conditions from top to bottom. The first true condition runs, and the rest are skipped."

left, right = st.columns([3, 2])

with left:
    st.subheader("Code editor")
    st.write("Type Python below. Ace handles editor behavior like indentation and tab support better than a plain text area.")

    code_value = st_ace(
        value=st.session_state.code_value,
        language="python",
        theme="github",
        key="python_editor",
        min_lines=18,
        max_lines=30,
        font_size=15,
        tab_size=4,
        show_gutter=True,
        wrap=True,
        auto_update=True,
    )

    if code_value is None:
        code_value = st.session_state.code_value
    else:
        st.session_state.code_value = code_value

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Normalize indentation", use_container_width=True):
            st.session_state.code_value = normalize_python_indentation(st.session_state.code_value)
            st.rerun()
    with c2:
        if st.button("Load sample", use_container_width=True):
            st.session_state.code_value = DEFAULT_CODE
            st.rerun()
    with c3:
        st.download_button(
            "Download .py",
            data=st.session_state.code_value,
            file_name="python_example.py",
            mime="text/x-python",
            use_container_width=True,
        )

    st.subheader("Saved code preview")
    st.code(st.session_state.code_value, language="python")

with right:
    st.subheader("Notes formatter")
    notes_input = st.text_area(
        "Explanation / notes",
        value=st.session_state.notes_value,
        height=180,
        help="This box is for readable notes, not runnable code.",
    )
    st.session_state.notes_value = notes_input

    wrap_width = st.slider("Wrap width", min_value=35, max_value=100, value=60)
    wrapped_notes = wrap_notes(st.session_state.notes_value, wrap_width)

    st.subheader("Spreadsheet-friendly notes")
    st.text_area(
        "Wrapped output",
        value=wrapped_notes,
        height=180,
        disabled=True,
    )

    st.download_button(
        "Download notes.txt",
        data=wrapped_notes,
        file_name="wrapped_notes.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.divider()

with st.expander("How to run this app"):
    st.markdown(
        """
        1. Create a virtual environment.
        2. Install the requirements.
        3. Run `streamlit run app.py`.

        This app uses the `streamlit-ace` component for the code editor.
        """
    )

