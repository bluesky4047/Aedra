import streamlit as st
from forms.register import register

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
                    # Judul form
                    st.title("Sign In", anchor=False)

                    # Input fields
                    username = st.text_input("", placeholder="🙍‍♂️ Username", label_visibility="collapsed")
                    password = st.text_input("", placeholder="🔒 Password", type="password", label_visibility="collapsed")

                    # Tombol Submit
                    if st.form_submit_button("Sign In", type="primary", use_container_width=True):
                        if username == "user1" and password == "user1":
                            st.session_state.logged_in = True
                            st.rerun()  # Rerun to reset the session state and display the logged-in view
                    
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