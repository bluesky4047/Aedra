import streamlit as st
import time

@st.dialog("Sign Up")
def register():
    with st.form("register"):
        new_username = st.text_input("Username Baru")
        new_password = st.text_input("Password Baru", type="password")
        confirm_password = st.text_input("Konfirmasi Password", type="password")
        
        if st.form_submit_button("Sign Up", type="primary", use_container_width=True):
            st.rerun()
            