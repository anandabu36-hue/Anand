import streamlit as st
from sarvamai import SarvamAI
from supabase import create_client
import time

st.set_page_config(page_title="Anand Translator FINAL", layout="centered")
st.title("Anand Translator - Voice 100% Works")

# 1. Secrets check
try:
    SARVAM_KEY = st.secrets["SARVAM_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets lo keys levu! Settings -> Secrets lo check chey")
    st.stop()

client = SarvamAI(api_subscription_key=SARVAM_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

# 2. Room
room = st.text_input("Room Code (rendu phone lo same pettu)", "ANAND123")
langs = {"Hindi":"hi-IN", "Telugu":"te-IN", "English":"en-IN", "Tamil":"ta-IN", "Kannada":"kn-IN"}

c1, c2 = st.columns(2)
with c1:
    my_lang = st.selectbox("Nee Bhasha", list(langs.keys()), 0)
with c2:
    target_lang = st.selectbox("Avathala ki ela vellali", list(langs.keys()), 1)

st.divider()

# 3. VOICE RECORD - webrtc kakunda simple mic
st.subheader("🎤 Ikkada matladu")
audio = st.audio_input("Record chey, tarvata automatic ga translate avuthundi")

if audio:
    with st.spinner("Sarvam STT..."):
        # Sarvam STT
        try:
            # Save temp
            with open("temp.wav","wb") as f:
                f.write(audio.getbuffer())
            
            with open("temp.wav","rb") as f:
                stt = client.speech_to_text.translate(
                    file=f,
                    language_code=langs[my_lang]
                )
            original = stt.transcript
            st.success(f"Nuvvu cheppindi ({my_lang}): {original}")

            # Translate to target
            tr = client.text.translate(
                input=original,
                source_language_code=langs[my_lang],
                target_language_code=langs[target_lang]
            )
            translated = tr.translated_text
            st.info(f"Translate ({target_lang}): {translated}")

            # Save to Supabase - Voice atu velledi ikkade!
            supabase.table("broadcasts").insert({
                "room_id": room,
                "sender_lang": langs[my_lang],
                "original_text": original,
                "translated_text": translated,
                "target_lang": langs[target_lang]
            }).execute()
            st.toast("✅ Supabase ki vellindi - Avathala phone lo kanipisthundi!")

            # TTS for you
            tts = client.text_to_speech.convert(
                text=translated,
                target_language_code=langs[target_lang]
            )
            st.audio(tts.audios[0], format="audio/wav")
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()
# 4. RECEIVE - Polling (Realtime kante stable)
st.subheader(f"📥 Room {room} - Live Messages (Avathala nundi)")

auto = st.checkbox("Auto Refresh On (Avathala voice kosam)", True)

if auto:
    placeholder = st.empty()
    for _ in range(100): # 100 times refresh
        try:
            res = supabase.table("broadcasts").select("*").eq("room_id", room).order("created_at", desc=True).limit(5).execute()
            with placeholder.container():
                for msg in res.data[::-1]:
                    if msg["sender_lang"] != langs[my_lang]: # only others
                        st.write(f"**Avathala:** {msg['original_text']} ({msg['sender_lang']})")
                        # Translate to MY language for me
                        try:
                            my_tr = client.text.translate(
                                input=msg['original_text'],
                                source_language_code=msg['sender_lang'],
                                target_language_code=langs[my_lang]
                            )
                            st.write(f"**Meeku ({my_lang}):** {my_tr.translated_text}")
                            # Play in MY language
                            my_tts = client.text_to_speech.convert(
                                text=my_tr.translated_text,
                                target_language_code=langs[my_lang]
                            )
                            st.audio(my_tts.audios[0], format="audio/wav")
                        except:
                            pass
                        st.divider()
        except Exception as e:
            st.error(f"Fetch error {e}")
        time.sleep(3)
else:
    if st.button("Refresh Messages"):
        res = supabase.table("broadcasts").select("*").eq("room_id", room).order("created_at", desc=True).limit(5).execute()
        st.json(res.data)
