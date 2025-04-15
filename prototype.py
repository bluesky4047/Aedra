import streamlit as st
import random
import time

# Streamed response emulator
def response_generator():
    response = random.choice(
        [
            "pertanyaan lanjutan",
            # "Hi, human! Is there anything I can help you with?",
            # "Do you need help?",
        ]
    )
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

def main():
    st.title("FeverScan")

    # Initialize chat history with assistant's opening message
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Assistant speaks first
        initial_message = "Halo Selamat datang di FeverScan, silahkan jawab beberapa pertanyaan berikut"
        st.session_state.messages.append({"role": "assistant", "content": initial_message})
        st.session_state.messages.append({"role": "assistant", "content": "pertanyaan 1"})

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            for word in response_generator():
                full_response += word
                placeholder.markdown(full_response)
            response = full_response  # store final response

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
