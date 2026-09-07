import streamlit as st

st.set_page_config(page_title="PDF Q&A", page_icon="PDF", layout="wide")

pages = [
    st.Page("pages/0_admin.py", title="Admin", icon=":material/admin_panel_settings:"),
    st.Page("pages/1_pdf_qna.py", title="PDF Q&A", icon=":material/chat:"),
]

navigation = st.navigation(pages)
navigation.run()
