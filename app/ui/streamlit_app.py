import streamlit as st

st.set_page_config(page_title="CentrAlign AI Task Worker", layout="wide")

st.title("🤖 CentrAlign AI — Autonomous Task Worker")
st.caption("Prototype scaffold — implementation coming next")

task = st.text_area(
    "Give the AI worker a task",
    "Find the latest invoice from Acme, update the finance system, and verify it."
)

if st.button("Run Autonomous Worker"):
    st.info("Agent execution loop has not been implemented yet.")
