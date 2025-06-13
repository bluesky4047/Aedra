import streamlit as st
import time
import bcrypt
import pymongo
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MODE PENGEMBANGAN - Set ke True untuk testing database tanpa Gemini
DEVELOPMENT_MODE = st.sidebar.checkbox("Mode Testing Database", value=False)

# Configure MongoDB connection
def connect_to_mongodb():
    mongo_uri = os.getenv("MONGODB_URI")
    client = pymongo.MongoClient(mongo_uri)
    db = client["Aedra_Ai"]  # Use the existing Aedra_Ai database
    users_collection = db["users"]  # Access the users collection
    return users_collection

def register_user(username, password, users_collection):
    if users_collection.find_one({"username": username}):
        return False, "Username sudah digunakan."

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    users_collection.insert_one({"username": username, "password": hashed_pw})
    return True, "Registrasi berhasil! Silakan login."

@st.dialog("Sign Up")
def register():
    users_collection = connect_to_mongodb()
    
    with st.form("register"):
        new_username = st.text_input("Username Baru")
        new_password = st.text_input("Password Baru", type="password")
        confirm_password = st.text_input("Konfirmasi Password", type="password")
        
        if st.form_submit_button("Sign Up", type="primary", use_container_width=True):
            if not new_username or not new_password or not confirm_password:
                st.error("Semua kolom harus diisi!")
            elif new_password != confirm_password:
                st.error("Password tidak cocok!")
            else:
                # Simulasi proses registrasi
                success, message = register_user(new_username, new_password, users_collection)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            time.sleep(1)
            st.rerun()