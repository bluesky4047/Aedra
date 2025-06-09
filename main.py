import streamlit as st
import bcrypt
from forms.register import register
from pymongo import MongoClient

# Initialize MongoDB client
client = MongoClient("localhost", 27017)
db_name = "feverscan"
db = client[db_name]

if db_name not in client.list_database_names():
    # Create the database if it doesn't exist
    # Optionally, create a collection to ensure the database is created
    db.create_collection("users")

def main_application():
    """Main Streamlit application"""
    # Authentication state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # Authentication menu
    if not st.session_state.logged_in:
            col_empty, col_main, col_empty2 = st.columns([1, 3, 1])  # Gunakan kolom untuk memusatkan form
            with col_main:
                with st.form("Sign In"):
                    account = db.users

                    # Judul form
                    st.title("Sign In", anchor=False)

                    # Input fields
                    username = st.text_input("", placeholder="🙍‍♂️ Username", label_visibility="collapsed")
                    password = st.text_input("", placeholder="🔒 Password", type="password", label_visibility="collapsed")

                    # Tombol Submit
                    if st.form_submit_button("Sign In", type="primary", use_container_width=True):
                        user_data = account.find_one({"username": username})  
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