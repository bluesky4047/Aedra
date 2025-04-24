import streamlit as st
import pymongo
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import uuid
import re

# Load environment variables
load_dotenv()

# Configure MongoDB connection
def connect_to_mongodb():
    mongo_uri = os.getenv("MONGODB_URI")
    client = pymongo.MongoClient(mongo_uri)
    db = client["Aedra_Ai"]  # Use the existing Aedra_Ai database
    history_collection = db["history"]  # Access the history collection
    users_collection = db["users"]      # Access the users collection
    return history_collection, users_collection

# Configure Gemini API
def configure_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-pro')
    return model

# Load reference data from CSV
@st.cache_data
def load_reference_data():
    try:
        df = pd.read_csv("DATA DBD.csv")
        return df
    except Exception as e:
        st.error(f"Error loading reference data: {e}")
        return pd.DataFrame()

# Process user responses with Gemini API for diagnosis
def analyze_symptoms(responses, reference_data, user_id):
    gemini_model = configure_gemini()
    
    # Create a prompt with the user's responses and reference data
    prompt = f"""
    Based on the following patient responses and the reference data, analyze the likelihood of dengue fever:
    
    Patient Responses:
    {responses}
    
    Reference Data (Brief Summary):
    {reference_data.head(5).to_string()}
    
    Provide a diagnosis in Bahasa Indonesia with the following information:
    1. Kemungkinan demam berdarah (Tinggi, Sedang, Rendah)
    2. Tindakan yang direkomendasikan berdasarkan gejala
    3. Tanda-tanda peringatan penting yang perlu diperhatikan
    4. Kapan harus segera mencari bantuan medis
    """
    
    response = gemini_model.generate_content(prompt)
    return response.text

# Process follow-up questions from users using Gemini API
def answer_followup_question(question, reference_data):
    gemini_model = configure_gemini()
    
    # Create a prompt with the user's question and reference constraints
    prompt = f"""
    Answer the following question about dengue fever in Bahasa Indonesia. Keep your response focused only on dengue fever (demam berdarah) related information. If the question is not related to dengue fever, politely redirect the conversation back to dengue fever topics.
    
    User question: {question}
    
    Reference Data (Brief Summary):
    {reference_data.head(5).to_string()}
    
    Your response should be informative, helpful, and medically accurate. Include a disclaimer if necessary that your information is not a substitute for professional medical advice.
    """
    
    response = gemini_model.generate_content(prompt)
    return response.text

# Save diagnosis to MongoDB
def save_to_mongodb(user_id, user_responses, diagnosis):
    try:
        history_collection, users_collection = connect_to_mongodb()
        
        # Save to history collection
        history_record = {
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "dengue_diagnosis",
            "responses": user_responses,
            "diagnosis": diagnosis
        }
        history_collection.insert_one(history_record)
        
        # Update user's last activity in users collection
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "last_activity": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "last_diagnosis_type": "dengue"
                },
                "$inc": {"diagnosis_count": 1}
            },
            upsert=True  # Create user if they don't exist
        )
        return True
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return False

# Save follow-up question to MongoDB
def save_followup_to_mongodb(user_id, question, answer):
    try:
        history_collection, users_collection = connect_to_mongodb()
        
        # Save to history collection
        history_record = {
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "followup_question",
            "question": question,
            "answer": answer
        }
        history_collection.insert_one(history_record)
        
        # Update user's last activity in users collection
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "last_activity": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "$inc": {"question_count": 1}
            },
            upsert=True
        )
        return True
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return False

# Get or create user_id
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    return st.session_state.user_id

# Define all questions
questions = [
    "Apakah Anda mengalami demam tinggi secara tiba-tiba (di atas 38°C)?",
    "Sudah berapa hari Anda mengalami demam?",
    "Apakah Anda merasa nyeri di belakang mata?",
    "Apakah Anda mengalami nyeri otot atau sendi yang parah (sering disebut 'breakbone fever')?",
    "Apakah Anda mengalami sakit kepala berat?",
    "Apakah Anda merasa sangat lelah atau lemas meskipun hanya sedikit aktivitas?",
    "Apakah Anda mengalami mual atau muntah?",
    "Apakah Anda mengalami ruam kulit atau bintik-bintik merah?",
    "Apakah Anda mengalami perdarahan ringan, seperti mimisan atau gusi berdarah?",
    "Apakah perut Anda terasa nyeri, terutama di bagian bawah kanan?",
    "Apakah Anda merasa pusing atau ingin pingsan saat berdiri?",
    "Apakah Anda kesulitan makan atau minum karena merasa mual atau lemas?"
]

# Options for each question
options = [
    ["Ya", "Tidak", "Tidak Yakin"],
    ["1 hari", "2–3 hari", "Lebih dari 3 hari"],
    ["Ya", "Tidak", "Tidak Yakin"],
    ["Ya", "Tidak", "Tidak Yakin"],
    ["Ya", "Tidak", "Tidak Yakin"],
    ["Ya", "Tidak", "Tidak Yakin"],
    ["Tidak", "Kadang", "Sering"],
    ["Ya", "Tidak", "Tidak Yakin"],
    ["Ya", "Tidak"],
    ["Ya", "Tidak", "Tidak Yakin"],
    ["Ya", "Tidak", "Kadang-kadang"],
    ["Tidak", "Sedikit", "Parah"]
]

st.title("FeverScan - Pemindai Demam Berdarah")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Assistant speaks first
    initial_message = "Halo! Selamat datang di FeverScan. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."
    st.session_state.messages.append({"role": "assistant", "content": initial_message})
    # Add first question immediately
    st.session_state.messages.append({"role": "assistant", "content": questions[0]})
    
if "current_question" not in st.session_state:
    st.session_state.current_question = 0
    
if "user_responses" not in st.session_state:
    st.session_state.user_responses = {}
    
if "diagnosis_complete" not in st.session_state:
    st.session_state.diagnosis_complete = False

if "allow_followup" not in st.session_state:
    st.session_state.allow_followup = False

# Ensure user has an ID
user_id = get_user_id()

# Load reference data
reference_data = load_reference_data()

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Check if we're in the diagnosis phase or follow-up phase
if not st.session_state.diagnosis_complete:
    # We're still in the diagnosis phase
    if st.session_state.current_question < len(questions):
        # Display option buttons for current question
        current_options = options[st.session_state.current_question]
        cols = st.columns(len(current_options))
        
        for i, option in enumerate(current_options):
            if cols[i].button(option, key=f"q{st.session_state.current_question}_option{i}"):
                # Store the user's response
                st.session_state.user_responses[questions[st.session_state.current_question]] = option
                
                # Add user response to chat history
                st.session_state.messages.append({"role": "user", "content": option})
                
                # Move to next question
                st.session_state.current_question += 1
                
                # Add the next question to messages if not at the end
                if st.session_state.current_question < len(questions):
                    next_question = questions[st.session_state.current_question]
                    st.session_state.messages.append({"role": "assistant", "content": next_question})
                
                # Force a rerun to update the UI
                st.rerun()
        
        # Allow for free text input as well
        user_input = st.text_input(
            "Atau ketikkan jawaban Anda sendiri:",
            key=f"text_input_{st.session_state.current_question}"
        )
        
        if st.button("Kirim Jawaban", key=f"submit_text_{st.session_state.current_question}"):
            if user_input:
                # Store the user's response
                st.session_state.user_responses[questions[st.session_state.current_question]] = user_input
                
                # Add user response to chat history
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Move to next question
                st.session_state.current_question += 1
                
                # Add the next question to messages if not at the end
                if st.session_state.current_question < len(questions):
                    next_question = questions[st.session_state.current_question]
                    st.session_state.messages.append({"role": "assistant", "content": next_question})
                
                # Force a rerun to update the UI
                st.rerun()
    else:
        # All questions answered, perform diagnosis
        if not st.session_state.diagnosis_complete:
            with st.spinner("Menganalisis gejala Anda..."):
                # Get diagnosis from Gemini
                diagnosis = analyze_symptoms(st.session_state.user_responses, reference_data, user_id)
                
                # Save to MongoDB
                save_to_mongodb(user_id, st.session_state.user_responses, diagnosis)
                
                # Add diagnosis to chat history
                st.session_state.messages.append({"role": "assistant", "content": diagnosis})
                
                # Add follow-up invitation
                followup_invitation = "Anda dapat bertanya lebih lanjut tentang demam berdarah atau memulai tes baru."
                st.session_state.messages.append({"role": "assistant", "content": followup_invitation})
                
                # Mark diagnosis as complete and allow follow-up
                st.session_state.diagnosis_complete = True
                st.session_state.allow_followup = True
                
                # Force a rerun to update the UI
                st.rerun()
else:
    # We're in the follow-up phase or showing test results
    if st.session_state.allow_followup:
        # Display test results and allow for follow-up questions
        
        # User input for follow-up questions
        user_question = st.text_input(
            "Tanyakan tentang demam berdarah:",
            key="followup_input"
        )
        
        # Process follow-up questions
        if st.button("Kirim Pertanyaan", key="submit_followup"):
            if user_question:
                # Add user question to chat history
                st.session_state.messages.append({"role": "user", "content": user_question})
                
                with st.spinner("Mencari jawaban..."):
                    # Get answer from Gemini
                    answer = answer_followup_question(user_question, reference_data)
                    
                    # Save to MongoDB
                    save_followup_to_mongodb(user_id, user_question, answer)
                    
                    # Add answer to chat history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # Force a rerun to update the UI
                st.rerun()
        
        # Button to start a new test
        if st.button("Mulai Tes Baru", key="new_test"):
            # Reset session state but keep user ID
            st.session_state.messages = []
            initial_message = "Halo! Selamat datang di FeverScan. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."
            st.session_state.messages.append({"role": "assistant", "content": initial_message})
            st.session_state.messages.append({"role": "assistant", "content": questions[0]})
            st.session_state.current_question = 0
            st.session_state.user_responses = {}
            st.session_state.diagnosis_complete = False
            st.session_state.allow_followup = False
            st.rerun()

# Add a sidebar with some information
with st.sidebar:
    st.header("Tentang FeverScan")
    st.write("""
    FeverScan adalah alat pemindai gejala demam berdarah yang menggunakan AI untuk membantu mengidentifikasi kemungkinan infeksi dengue berdasarkan gejala-gejala yang Anda alami.
    
    **Catatan Penting**: Alat ini tidak menggantikan diagnosis medis profesional. Selalu konsultasikan dengan tenaga medis untuk diagnosis dan perawatan yang tepat.
    """)
    
    st.header("Tanda Peringatan Demam Berdarah")
    st.write("""
    Segera cari bantuan medis jika mengalami:
    - Nyeri perut yang parah
    - Muntah terus-menerus
    - Perdarahan dari hidung atau gusi
    - Bintik-bintik merah di kulit
    - Kesulitan bernapas
    - Darah dalam muntahan atau feses
    """)