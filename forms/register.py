import streamlit as st
import time
import bcrypt
from pymongo import MongoClient

# Initialize MongoDB client
client = MongoClient("localhost", 27017)
db_name = "feverscan"
db = client[db_name]
users_col = db["users"]

def register_user(username, password):
    if users_col.find_one({"username": username}):
        return False, "Username sudah digunakan."

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    users_col.insert_one({"username": username, "password": hashed_pw})
    return True, "Registrasi berhasil! Silakan login."

@st.dialog("Sign Up")
def register():
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
                success, message = register_user(new_username, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            time.sleep(1)
            st.rerun()
            