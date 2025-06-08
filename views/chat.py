import streamlit as st
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

# Load environment variables
load_dotenv()

# MODE PENGEMBANGAN - Set ke True untuk testing database tanpa Gemini
DEVELOPMENT_MODE = st.sidebar.checkbox("Mode Testing Database", value=False)

# Configure MongoDB connection
def connect_to_mongodb():
    mongo_uri = os.getenv("MONGODB_URI")
    client = pymongo.MongoClient(mongo_uri)
    db = client["Aedra_Ai"]  # Use the existing Aedra_Ai database
    history_collection = db["history"]  # Access the history collection
    users_collection = db["users"]      # Access the users collection
    return history_collection, users_collection

# Test koneksi MongoDB
def test_mongodb_connection():
    try:
        history_collection, users_collection = connect_to_mongodb()
        
        # Test ping database
        client = history_collection.database.client
        client.admin.command('ping')
        
        # Hitung jumlah dokumen di setiap collection
        history_count = history_collection.count_documents({})
        users_count = users_collection.count_documents({})
        
        st.success(f"✅ Koneksi MongoDB berhasil!")
        st.info(f"📊 Data history: {history_count} dokumen")
        st.info(f"👥 Data users: {users_count} dokumen")
        
        return True, history_collection, users_collection
    except Exception as e:
        st.error(f"❌ Koneksi MongoDB gagal: {e}")
        return False, None, None

# Configure Gemini API
def configure_gemini():
    if DEVELOPMENT_MODE:
        return None  # Tidak konfigurasi Gemini di mode testing
    
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    return model

# Load reference data from CSV
@st.cache_data
def load_reference_data():
    try:
        df = pd.read_csv("views/DATA DBD.csv")
        return df
    except Exception as e:
        st.error(f"Error loading reference data: {e}")
        return pd.DataFrame()

# MOCK RESPONSES untuk testing - tanpa Gemini
def get_mock_diagnosis(responses):
    """Memberikan diagnosis palsu untuk testing database"""
    
    # Hitung score berdasarkan jawaban
    risk_score = 0
    total_questions = len(responses)
    
    for question, answer in responses.items():
        if "ya" in answer.lower():
            risk_score += 2
        elif "sering" in answer.lower() or "parah" in answer.lower():
            risk_score += 2
        elif "kadang" in answer.lower() or "sedang" in answer.lower():
            risk_score += 1
        elif "lebih dari 3 hari" in answer.lower():
            risk_score += 2
        elif "2-3 hari" in answer.lower():
            risk_score += 1
    
    # Tentukan tingkat risiko
    risk_percentage = (risk_score / (total_questions * 2)) * 100
    
    if risk_percentage >= 70:
        risk_level = "TINGGI"
        color_icon = "🔴"
    elif risk_percentage >= 40:
        risk_level = "SEDANG" 
        color_icon = "🟡"
    else:
        risk_level = "RENDAH"
        color_icon = "🟢"
    
    diagnosis = f"""
**{color_icon} HASIL ANALISIS GEJALA DEMAM BERDARAH (MODE TESTING)**

**Kemungkinan Demam Berdarah: {risk_level}**
*Score: {risk_score}/{total_questions * 2} ({risk_percentage:.1f}%)*

🩺 **Tindakan yang Direkomendasikan:**
- {"Segera konsultasi dengan dokter atau kunjungi rumah sakit" if risk_percentage >= 70 else "Konsultasi dengan dokter untuk pemeriksaan lebih lanjut" if risk_percentage >= 40 else "Pantau gejala dan istirahat yang cukup"}
- Perbanyak minum air putih untuk mencegah dehidrasi
- Istirahat yang cukup
- Pantau suhu tubuh secara berkala

⚠️ **Tanda Peringatan Penting:**
- Nyeri perut yang hebat dan terus-menerus
- Muntah terus-menerus (lebih dari 3x dalam sehari)  
- Perdarahan dari hidung, gusi, atau bintik merah di kulit
- Sesak napas atau kesulitan bernapas
- Penurunan kesadaran atau gelisah

🚨 **Segera Cari Bantuan Medis Jika:**
- Demam tinggi tidak turun setelah 3 hari
- Muncul tanda-tanda perdarahan
- Muntah darah atau BAB berdarah
- Pingsan atau penurunan kesadaran

**📝 Catatan Testing:**
- Ini adalah response MOCK untuk testing database
- Data telah disimpan ke MongoDB
- Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S")}
- User ID: {st.session_state.get('user_id', 'unknown')}

⚠️ **Disclaimer:** Hasil ini hanya untuk testing sistem. Konsultasi dengan tenaga medis profesional untuk diagnosis yang akurat.
"""
    
    return diagnosis

def get_mock_followup_answer(question):
    """Memberikan jawaban palsu untuk pertanyaan lanjutan"""
    
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['pencegahan', 'cegah', 'hindari']):
        return """
**PENCEGAHAN DEMAM BERDARAH (MODE TESTING)**

🏠 **3M Plus:**
- **Menguras:** Bak mandi, tandon air minimal 1 minggu sekali
- **Menutup:** Tempat penampungan air rapat-rapat
- **Mengubur:** Barang bekas yang bisa menampung air

➕ **Plus:**
- Gunakan obat nyamuk/anti nyamuk
- Pasang kawat kasa di ventilasi
- Pakai baju lengan panjang
- Tanam tanaman pengusir nyamuk

*📝 Ini adalah response MOCK untuk testing database*
"""
    
    elif any(word in question_lower for word in ['gejala', 'tanda']):
        return """
**GEJALA DEMAM BERDARAH (MODE TESTING)**

🌡️ **Gejala Utama:**
- Demam tinggi mendadak (38-40°C)
- Sakit kepala hebat
- Nyeri di belakang mata
- Nyeri otot dan sendi

🔍 **Gejala Lanjutan:**
- Ruam kulit atau bintik merah
- Mual dan muntah
- Perdarahan ringan (mimisan, gusi berdarah)

*📝 Ini adalah response MOCK untuk testing database*
"""
    
    elif any(word in question_lower for word in ['obat', 'pengobatan', 'terapi']):
        return """
**PENGOBATAN DEMAM BERDARAH (MODE TESTING)**

💊 **Tidak Ada Obat Khusus:**
- Belum ada obat antiviral spesifik untuk dengue
- Pengobatan bersifat suportif

🏥 **Perawatan:**
- Istirahat total
- Minum banyak air putih
- Kompres untuk menurunkan demam
- Pantau jumlah trombosit

⚠️ **Hindari:** Aspirin dan ibuprofen

*📝 Ini adalah response MOCK untuk testing database*
"""
    
    else:
        return f"""
**INFORMASI UMUM DEMAM BERDARAH (MODE TESTING)**

Terima kasih atas pertanyaan: "{question}"

🦟 **Tentang Demam Berdarah:**
- Penyakit yang disebabkan virus dengue
- Ditularkan melalui gigitan nyamuk Aedes aegypti
- Masa inkubasi 4-7 hari
- Bisa menyerang siapa saja

📞 **Untuk informasi lebih lanjut, hubungi:**
- Puskesmas terdekat
- Hotline kesehatan daerah
- Dokter keluarga

*📝 Ini adalah response MOCK untuk testing database - Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S")}*

**Disclaimer:** Ini adalah response untuk testing. Selalu konsultasi dengan tenaga medis profesional.
"""

# Process user responses - dengan pilihan REAL atau MOCK
def analyze_symptoms(responses, reference_data, user_id):
    if DEVELOPMENT_MODE:
        # Mode testing - gunakan mock response
        st.info("🧪 Mode Testing: Menggunakan response palsu (tidak memanggil Gemini)")
        time.sleep(1)  # Simulasi loading
        return get_mock_diagnosis(responses)
    else:
        # Mode production - gunakan Gemini API (kode asli Anda)
        try:
            gemini_model = configure_gemini()
            
            symptom_summary = []
            for question, answer in responses.items():
                if "demam" in question.lower():
                    symptom_summary.append(f"Demam: {answer}")
                elif "nyeri" in question.lower():
                    symptom_summary.append(f"Nyeri: {answer}")
                elif "lelah" in question.lower():
                    symptom_summary.append(f"Kelelahan: {answer}")
                elif "mual" in question.lower():
                    symptom_summary.append(f"Mual/Muntah: {answer}")
                elif "ruam" in question.lower():
                    symptom_summary.append(f"Ruam kulit: {answer}")
                elif "perdarahan" in question.lower():
                    symptom_summary.append(f"Perdarahan: {answer}")
            
            prompt = f"""
            Analisis gejala demam berdarah dalam Bahasa Indonesia:
            
            Gejala pasien: {'; '.join(symptom_summary)}
            
            Berikan:
            1. Kemungkinan demam berdarah (Tinggi/Sedang/Rendah)
            2. Tindakan direkomendasikan
            3. Tanda peringatan penting
            4. Kapan mencari bantuan medis
            
            Jawaban singkat dan jelas.
            """
            
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Error calling Gemini API: {e}")
            st.info("Menggunakan fallback response...")
            return get_mock_diagnosis(responses)

# Process follow-up questions - dengan pilihan REAL atau MOCK
def answer_followup_question(question, reference_data):
    if DEVELOPMENT_MODE:
        # Mode testing - gunakan mock response
        st.info("🧪 Mode Testing: Menggunakan response palsu untuk pertanyaan lanjutan")
        time.sleep(1)  # Simulasi loading
        return get_mock_followup_answer(question)
    else:
        # Mode production - gunakan Gemini API (kode asli Anda)
        try:
            gemini_model = configure_gemini()
            
            prompt = f"""
            Jawab pertanyaan tentang demam berdarah dalam Bahasa Indonesia:
            
            Pertanyaan: {question}
            
            Berikan jawaban singkat, akurat, dan medis. Jika tidak terkait demam berdarah, 
            arahkan kembali ke topik demam berdarah.
            
            Sertakan disclaimer bahwa ini bukan pengganti konsultasi medis profesional.
            """
            
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Error calling Gemini API: {e}")
            st.info("Menggunakan fallback response...")
            return get_mock_followup_answer(question)

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
            "diagnosis": diagnosis,
            "mode": "testing" if DEVELOPMENT_MODE else "production"  # Tambah info mode
        }
        result = history_collection.insert_one(history_record)
        
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
        
        if DEVELOPMENT_MODE:
            st.success(f"✅ Data berhasil disimpan ke MongoDB! ID: {result.inserted_id}")
        
        return True
    except Exception as e:
        st.error(f"❌ Error saving to database: {e}")
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
            "answer": answer,
            "mode": "testing" if DEVELOPMENT_MODE else "production"  # Tambah info mode
        }
        result = history_collection.insert_one(history_record)
        
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
        
        if DEVELOPMENT_MODE:
            st.success(f"✅ Pertanyaan berhasil disimpan! ID: {result.inserted_id}")
        
        return True
    except Exception as e:
        st.error(f"❌ Error saving to database: {e}")
        return False

# Get or create user_id
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    return st.session_state.user_id

# Tampilkan data dari database untuk testing
def show_database_data():
    if DEVELOPMENT_MODE:
        st.sidebar.header("🗃️ Data Database")
        
        try:
            history_collection, users_collection = connect_to_mongodb()
            
            # Tampilkan data history terbaru
            recent_history = list(history_collection.find().sort("timestamp", -1).limit(5))
            if recent_history:
                st.sidebar.subheader("History Terbaru:")
                for item in recent_history[:3]:  # Tampilkan 3 teratas
                    st.sidebar.text(f"• {item.get('type', 'unknown')} - {item.get('timestamp', 'no time')}")
            
            # Tampilkan statistik users
            total_users = users_collection.count_documents({})
            st.sidebar.metric("Total Users", total_users)
            
            # Button untuk melihat semua data
            if st.sidebar.button("Lihat Semua Data"):
                st.sidebar.json(recent_history[0] if recent_history else {"message": "No data"})
                
        except Exception as e:
            st.sidebar.error(f"Error mengambil data: {e}")

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

st.title("Aedra - Pemindai Demam Berdarah")

# Tampilkan mode yang aktif
if DEVELOPMENT_MODE:
    st.warning("🧪 **MODE TESTING DATABASE AKTIF** - Tidak menggunakan Gemini API")
    # Test koneksi database di awal
    db_connected, hist_col, users_col = test_mongodb_connection()
else:
    st.info("🚀 **MODE PRODUCTION** - Menggunakan Gemini API")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Assistant speaks first
    mode_text = " (Mode Testing)" if DEVELOPMENT_MODE else ""
    initial_message = f"Halo! Selamat datang di Aedra{mode_text}. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."
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

# Tampilkan data database jika dalam mode testing
show_database_data()

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
            loading_text = "Menganalisis gejala Anda..." if not DEVELOPMENT_MODE else "Testing database - Membuat response palsu..."
            with st.spinner(loading_text):
                # Get diagnosis (REAL atau MOCK tergantung mode)
                diagnosis = analyze_symptoms(st.session_state.user_responses, reference_data, user_id)
                
                # Save to MongoDB (selalu disimpan untuk testing)
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
                
                loading_text = "Mencari jawaban..." if not DEVELOPMENT_MODE else "Testing database - Membuat jawaban palsu..."
                with st.spinner(loading_text):
                    # Get answer (REAL atau MOCK tergantung mode)
                    answer = answer_followup_question(user_question, reference_data)
                    
                    # Save to MongoDB (selalu disimpan untuk testing)
                    save_followup_to_mongodb(user_id, user_question, answer)
                    
                    # Add answer to chat history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # Force a rerun to update the UI
                st.rerun()
        
        # Button to start a new test
        if st.button("Mulai Tes Baru", key="new_test"):
            # Reset session state but keep user ID
            st.session_state.messages = []
            mode_text = " (Mode Testing)" if DEVELOPMENT_MODE else ""
            initial_message = f"Halo! Selamat datang di Aedra{mode_text}. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."
            st.session_state.messages.append({"role": "assistant", "content": initial_message})
            st.session_state.messages.append({"role": "assistant", "content": questions[0]})
            st.session_state.current_question = 0
            st.session_state.user_responses = {}
            st.session_state.diagnosis_complete = False
            st.session_state.allow_followup = False
            st.rerun()

# Add a sidebar with some information
with st.sidebar:
    # Status Mode
    st.header("Status Sistem")
    if DEVELOPMENT_MODE:
        st.success("🧪 Mode Testing Database")
        st.info("""
        **Mode Testing Aktif:**
        - ✅ Database MongoDB digunakan
        - ❌ Gemini API tidak dipanggil
        - 🔧 Response menggunakan data palsu
        - 💾 Semua data tetap disimpan ke database
        """)
    else:
        st.info("🚀 Mode Production")
        st.warning("""
        **Mode Production:**
        - ✅ Menggunakan Gemini API
        - ⚠️ Memerlukan quota API
        - 💰 Ada biaya penggunaan
        """)
    
    # Informasi User ID untuk tracking
    st.header("Info Session")
    st.text(f"User ID: {get_user_id()[:8]}...")
    st.text(f"Timestamp: {time.strftime('%H:%M:%S')}")