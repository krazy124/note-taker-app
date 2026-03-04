import streamlit as st

st.title("My First Deployed App")

name = st.text_input("Enter your name")

if name:
    st.write(f"Hello {name}, welcome to my app.")
