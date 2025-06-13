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

# Configure MongoDB connection
def connect_to_mongodb():
    mongo_uri = os.getenv("MONGODB_URI")
    try:
        client = pymongo.MongoClient(mongo_uri)
        db = client["Aedra_Ai"]  # Use the existing Aedra_Ai database
        history_collection = db["history"]  # Access the history collection
        users_collection = db["users"]      # Access the users collection
        return history_collection, users_collection
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke MongoDB: {e}")
        st.stop() # Stop execution if database connection fails

# Test koneksi MongoDB (hanya untuk debugging awal, tidak dipanggil di sidebar utama)
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
    if st.session_state.DEVELOPMENT_MODE: # Menggunakan st.session_state untuk DEVELOPMENT_MODE
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
    if st.session_state.DEVELOPMENT_MODE: # Menggunakan st.session_state
        # Mode testing - gunakan mock response
        st.info("🧪 Mode Testing: Menggunakan response palsu (tidak memanggil Gemini)")
        time.sleep(1)  # Simulasi loading
        return get_mock_diagnosis(responses)
    else:
        # Mode production - gunakan Gemini API
        try:
            gemini_model = configure_gemini()
            
            symptom_summary = []
            for question, answer in responses.items():
                # Improved symptom extraction based on keywords
                if "demam" in question.lower():
                    symptom_summary.append(f"Demam: {answer}")
                elif "nyeri" in question.lower() and ("mata" in question.lower() or "otot" in question.lower() or "sendi" in question.lower()):
                    symptom_summary.append(f"Nyeri: {answer}")
                elif "lelah" in question.lower() or "lemas" in question.lower():
                    symptom_summary.append(f"Kelelahan/Kelemasan: {answer}")
                elif "mual" in question.lower() or "muntah" in question.lower():
                    symptom_summary.append(f"Mual/Muntah: {answer}")
                elif "ruam" in question.lower() or "bintik" in question.lower():
                    symptom_summary.append(f"Ruam kulit: {answer}")
                elif "perdarahan" in question.lower():
                    symptom_summary.append(f"Perdarahan: {answer}")
                elif "sakit kepala" in question.lower():
                    symptom_summary.append(f"Sakit kepala: {answer}")
                elif "perut" in question.lower():
                    symptom_summary.append(f"Nyeri perut: {answer}")
                elif "pusing" in question.lower() or "pingsan" in question.lower():
                    symptom_summary.append(f"Pusing/Pingsan: {answer}")
                elif "makan" in question.lower() or "minum" in question.lower():
                    symptom_summary.append(f"Kesulitan makan/minum: {answer}")
                else: # Fallback for any other questions
                    symptom_summary.append(f"{question.split(' ')[1]}: {answer}") # Take the second word of question as generic symptom

            
            prompt = f"""
            Analisis gejala demam berdarah dalam Bahasa Indonesia:
            
            Gejala pasien: {'; '.join(symptom_summary)}.
            
            Berikan:
            1. Kemungkinan demam berdarah (Tinggi/Sedang/Rendah)
            2. Tindakan direkomendasikan
            3. Tanda peringatan penting
            4. Kapan mencari bantuan medis
            
            Jawaban singkat, jelas, dan menggunakan format Markdown untuk poin-poin.
            """
            
            response = gemini_model.generate_content(prompt)
            return response.text
        except ResourceExhausted:
            st.error("❌ Kuota Gemini API habis atau batas rate tercapai. Coba lagi nanti.")
            st.info("Menggunakan fallback response (mock diagnosis)...")
            return get_mock_diagnosis(responses)
        except DeadlineExceeded:
            st.error("❌ Permintaan ke Gemini API timeout. Koneksi mungkin lambat atau server sibuk.")
            st.info("Menggunakan fallback response (mock diagnosis)...")
            return get_mock_diagnosis(responses)
        except Exception as e:
            st.error(f"Error calling Gemini API: {e}")
            st.info("Menggunakan fallback response (mock diagnosis)...")
            return get_mock_diagnosis(responses)

# Process follow-up questions - dengan pilihan REAL atau MOCK
def answer_followup_question(question, reference_data):
    if st.session_state.DEVELOPMENT_MODE: # Menggunakan st.session_state
        # Mode testing - gunakan mock response
        st.info("🧪 Mode Testing: Menggunakan response palsu untuk pertanyaan lanjutan")
        time.sleep(1)  # Simulasi loading
        return get_mock_followup_answer(question)
    else:
        # Mode production - gunakan Gemini API
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
        except ResourceExhausted:
            st.error("❌ Kuota Gemini API habis atau batas rate tercapai. Coba lagi nanti.")
            st.info("Menggunakan fallback response (mock jawaban)...")
            return get_mock_followup_answer(question)
        except DeadlineExceeded:
            st.error("❌ Permintaan ke Gemini API timeout. Koneksi mungkin lambat atau server sibuk.")
            st.info("Menggunakan fallback response (mock jawaban)...")
            return get_mock_followup_answer(question)
        except Exception as e:
            st.error(f"Error calling Gemini API: {e}")
            st.info("Menggunakan fallback response (mock jawaban)...")
            return get_mock_followup_answer(question)

# Save diagnosis to MongoDB
def save_to_mongodb(user_id, user_responses, diagnosis):
    try:
        history_collection, users_collection = connect_to_mongodb()
        
        # Reconstruct conversation messages for this diagnosis
        conversation = [
            {"role": "assistant", "content": f"Halo! Selamat datang di Aedra{' (Mode Testing)' if st.session_state.DEVELOPMENT_MODE else ''}. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."}
        ]
        for question in questions:
            if question in user_responses:
                conversation.append({"role": "assistant", "content": question})
                conversation.append({"role": "user", "content": user_responses[question]})
        conversation.append({"role": "assistant", "content": diagnosis})
        conversation.append({"role": "assistant", "content": "Anda dapat bertanya lebih lanjut tentang demam berdarah atau memulai tes baru."})
        
        # Save to history collection
        history_record = {
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "dengue_diagnosis",
            "responses": user_responses,
            "diagnosis": diagnosis,
            "conversation": conversation,
            "mode": "testing" if st.session_state.DEVELOPMENT_MODE else "production"
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
            upsert=True
        )
        
        if st.session_state.DEVELOPMENT_MODE:
            st.success(f"✅ Data diagnosis berhasil disimpan ke MongoDB! ID: {result.inserted_id}")
        
        return True
    except Exception as e:
        st.error(f"❌ Error saving diagnosis to database: {e}")
        return False

# Save follow-up question to MongoDB
def save_followup_to_mongodb(user_id, question, answer):
    try:
        history_collection, users_collection = connect_to_mongodb()
        
        # Reconstruct conversation for this follow-up
        conversation = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        # Save to history collection
        history_record = {
            "user_id": user_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "followup_question",
            "question": question,
            "answer": answer,
            "conversation": conversation,
            "mode": "testing" if st.session_state.DEVELOPMENT_MODE else "production"
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
        
        if st.session_state.DEVELOPMENT_MODE:
            st.success(f"✅ Pertanyaan lanjutan berhasil disimpan! ID: {result.inserted_id}")
        
        return True
    except Exception as e:
        st.error(f"❌ Error saving follow-up question to database: {e}")
        return False

# Get or create user_id
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    return st.session_state.user_id

# Get conversation history from MongoDB for sidebar display
def get_conversation_history(user_id):
    history_collection, _ = connect_to_mongodb()
    # Fetch history for the current user, sorted by timestamp descending
    # Include conversation field for reloading chats
    return list(history_collection.find(
        {"user_id": user_id},
        {
            "type": 1,
            "timestamp": 1,
            "question": 1,
            "diagnosis": 1,
            "conversation": 1,
            "_id": 1  # Include _id for clickable buttons
        }
    ).sort("timestamp", pymongo.DESCENDING).limit(10))

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

# Initialize session state for DEVELOPMENT_MODE if not already set
if "DEVELOPMENT_MODE" not in st.session_state:
    st.session_state.DEVELOPMENT_MODE = False

# Ensure user has an ID
user_id = get_user_id()

# Load reference data
reference_data = load_reference_data()

# --- Sidebar Content ---
with st.sidebar:
    st.header("🤖 Aedra AI")
    st.text(f"User ID: {user_id[:8]}...")
    st.text(f"Timestamp: {time.strftime('%H:%M:%S')}")

    # DEVELOPMENT_MODE checkbox
    st.session_state.DEVELOPMENT_MODE = st.checkbox("Mode Testing Database", value=st.session_state.DEVELOPMENT_MODE)
    if st.session_state.DEVELOPMENT_MODE:
        st.warning("🧪 **MODE TESTING DATABASE AKTIF** - Tidak menggunakan Gemini API")
    else:
        st.info("🚀 **MODE PRODUCTION** - Menggunakan Gemini API")

    st.header("📚 Riwayat Percakapan")
    history = get_conversation_history(user_id)

    if history:
        for entry in history:
            entry_type = entry.get("type", "unknown")
            timestamp = entry.get("timestamp", "No Timestamp").split(' ')[1]  # Just show time
            entry_id = str(entry["_id"])  # MongoDB ObjectId for button key

            if entry_type == "dengue_diagnosis":
                diagnosis_text = entry.get("diagnosis", "")
                match = re.search(r"Kemungkinan Demam Berdarah:\s*(\w+)", diagnosis_text)
                risk_level = match.group(1) if match else "N/A"
                label = f"Diagnosis ({timestamp}) - Risiko: {risk_level}"
                if st.button(label, key=f"history_{entry_id}"):
                    # Load the conversation into session state
                    st.session_state.messages = entry.get("conversation", [])
                    st.session_state.diagnosis_complete = True
                    st.session_state.allow_followup = True
                    st.session_state.current_question = len(questions)
                    st.session_state.user_responses = entry.get("responses", {})
                    st.rerun()
            elif entry_type == "followup_question":
                question_text = entry.get("question", "Tidak ada pertanyaan")
                display_question = (question_text[:40] + '...') if len(question_text) > 40 else question_text
                label = f"Tanya ({timestamp}) - {display_question}"
                if st.button(label, key=f"history_{entry_id}"):
                    # Load the conversation into session state
                    st.session_state.messages = entry.get("conversation", [])
                    st.session_state.diagnosis_complete = True
                    st.session_state.allow_followup = True
                    st.session_state.current_question = len(questions)
                    st.session_state.user_responses = {}  # Clear responses for follow-up
                    st.rerun()
    else:
        st.info("Belum ada riwayat percakapan.")

# --- Main Chat Interface ---

# Display the mode active in the main area
if st.session_state.DEVELOPMENT_MODE:
    st.warning("🧪 **MODE TESTING DATABASE AKTIF** - Tidak menggunakan Gemini API. Menggunakan response palsu dan menyimpan ke DB.")
else:
    st.info("🚀 **MODE PRODUCTION** - Menggunakan Gemini API. Memerlukan kuota API.")

# Initialize session state for chat flow
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Assistant speaks first
    mode_text = " (Mode Testing)" if st.session_state.DEVELOPMENT_MODE else ""
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

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Check if we're in the diagnosis phase or follow-up phase
if not st.session_state.diagnosis_complete:
    # We're still in the diagnosis phase
    if st.session_state.current_question < len(questions):
        # Display current question in the main chat (if not already displayed)
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != questions[st.session_state.current_question]:
             st.session_state.messages.append({"role": "assistant", "content": questions[st.session_state.current_question]})
             st.rerun()

        # Display option buttons for current question
        current_options = options[st.session_state.current_question]
        cols = st.columns(len(current_options))
        
        button_clicked = False
        for i, option in enumerate(current_options):
            if cols[i].button(option, key=f"q{st.session_state.current_question}_option{i}"):
                # Store the user's response
                st.session_state.user_responses[questions[st.session_state.current_question]] = option
                
                # Add user response to chat history
                st.session_state.messages.append({"role": "user", "content": option})
                
                # Move to next question
                st.session_state.current_question += 1
                button_clicked = True
                break

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
                button_clicked = True
            else:
                st.warning("Mohon masukkan jawaban atau pilih opsi.")
        
        if button_clicked:
            st.rerun()
    else:
        # All questions answered, perform diagnosis
        if not st.session_state.diagnosis_complete:
            loading_text = "Menganalisis gejala Anda..." if not st.session_state.DEVELOPMENT_MODE else "Testing database - Membuat response palsu..."
            with st.spinner(loading_text):
                # Get diagnosis
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
        # User input for follow-up questions
        user_question = st.chat_input(
            "Tanyakan tentang demam berdarah atau ketik 'mulai tes baru' untuk memulai ulang:"
        )
        
        # Process follow-up questions or new test command
        if user_question:
            if user_question.lower().strip() == "mulai tes baru":
                # Reset session state but keep user ID
                st.session_state.messages = []
                mode_text = " (Mode Testing)" if st.session_state.DEVELOPMENT_MODE else ""
                initial_message = f"Halo! Selamat datang di Aedra{mode_text}. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."
                st.session_state.messages.append({"role": "assistant", "content": initial_message})
                st.session_state.messages.append({"role": "assistant", "content": questions[0]})
                st.session_state.current_question = 0
                st.session_state.user_responses = {}
                st.session_state.diagnosis_complete = False
                st.session_state.allow_followup = False
                st.rerun()
            else:
                # Add user question to chat history
                st.session_state.messages.append({"role": "user", "content": user_question})
                
                loading_text = "Mencari jawaban..." if not st.session_state.DEVELOPMENT_MODE else "Testing database - Membuat jawaban palsu..."
                with st.spinner(loading_text):
                    # Get answer
                    answer = answer_followup_question(user_question, reference_data)
                    
                    # Save to MongoDB
                    save_followup_to_mongodb(user_id, user_question, answer)
                    
                    # Add answer to chat history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # Force a rerun to update the UI
                st.rerun()

    # Button to start a new test
    if st.button("Mulai Tes Baru", key="new_test_button"):
        # Reset session state but keep user ID
        st.session_state.messages = []
        mode_text = " (Mode Testing)" if st.session_state.DEVELOPMENT_MODE else ""
        initial_message = f"Halo! Selamat datang di Aedra{mode_text}. Saya akan membantu Anda menilai gejala-gejala yang mungkin terkait dengan demam berdarah (dengue fever). Mari kita mulai dengan beberapa pertanyaan."
        st.session_state.messages.append({"role": "assistant", "content": initial_message})
        st.session_state.messages.append({"role": "assistant", "content": questions[0]})
        st.session_state.current_question = 0
        st.session_state.user_responses = {}
        st.session_state.diagnosis_complete = False
        st.session_state.allow_followup = False
        st.rerun()