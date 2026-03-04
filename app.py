import streamlit as st

st.title("My First Deployed App")

st.write("This app is running from GitHub and Streamlit Cloud.")

name = st.text_input("Enter your name")

if name:
    st.write(f"Hello {name}, welcome to my app.")
