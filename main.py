import streamlit as st
import bcrypt
import pymongo
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import uuid
import re
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded
import random
from forms.register import register

# Load environment variables
load_dotenv()

# MODE PENGEMBANGAN - Set ke True untuk testing database tanpa Gemini
# DEVELOPMENT_MODE = st.sidebar.checkbox("Mode Testing Database", value=False)

# Configure MongoDB connection
def connect_to_mongodb():
    mongo_uri = os.getenv("MONGODB_URI")
    client = pymongo.MongoClient(mongo_uri)
    db = client["Aedra_Ai"]  # Use the existing Aedra_Ai database
    history_collection = db["history"]  # Access the history collection
    users_collection = db["users"]      # Access the users collection
    return history_collection, users_collection

def main_application():
    """Main Streamlit application"""
    # Initialize MongoDB collections
    history_collection, users_collection = connect_to_mongodb()

    # Authentication state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # Authentication menu
    if not st.session_state.logged_in:
        col_empty, col_main, col_empty2 = st.columns([1, 3, 1])  # Gunakan kolom untuk memusatkan form
        with col_main:
            with st.form("Sign In"):
                # Judul form
                st.title("Sign In", anchor=False)

                # Input fields
                username = st.text_input("", placeholder="🙍‍♂️ Username", label_visibility="collapsed")
                password = st.text_input("", placeholder="🔒 Password", type="password", label_visibility="collapsed")

                # Tombol Submit
                if st.form_submit_button("Sign In", type="primary", use_container_width=True):
                    user_data = users_collection.find_one({"username": username})  
                    if user_data and bcrypt.checkpw(password.encode(), user_data["password"]):
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("Username atau password salah. Silakan coba lagi.")
                
                col1, col2 = st.columns(2)
                col1.write("Don't have an account?")
                if col2.form_submit_button("Sign Up", type="secondary", use_container_width=True):
                    register()

    else:
        # Display main content after login
        chat = st.Page(
            page="views/chat.py",
            title="Chat",
            icon=":material/dashboard:",
            default=True,
        )
        pg = st.navigation(
            {
                "MENU": [chat]
            }
        )
        pg.run()

if __name__ == "__main__":
    main_application()