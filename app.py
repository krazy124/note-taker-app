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
