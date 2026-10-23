import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import uuid

st.set_page_config(page_title="Anand Live Translator", layout="centered")

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# Languages - Nee Idea Prakaram
LANGS = {
    "Telugu - తెలుగు": "te",
    "Hindi - हिंदी": "hi",
    "English": "en",
    "Tamil - தமிழ்": "ta",
    "Kannada - ಕನ್ನಡ": "kn"
}

for k,v in {"auth":False,"room":None,"my_lang":"te","other_lang":"hi","translated":""}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>🔒 Anand Translator</h2>", unsafe_allow_html=True)
    with st.form("l"):
        p=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary") and p=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Live Call Translator</h2><p style='text-align:center;color:#888'>Your Idea - Language Button in Call</p>", unsafe_allow_html=True)
    st.info("**How it works:** A calls in Hindi -> You hear Telugu -> You reply Telugu -> A hears Hindi")
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call", use_container_width=True, type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        with st.form("j"):
            code=st.text_input("Room Code ANAND-XXXXX")
            if st.form_submit_button("Join", use_container_width=True):
                st.session_state.room=code.upper().strip(); st.rerun()
    st.stop()

# --- CALL SCREEN - Nee Idea lo Language Button ---
st.markdown(f"""
<div style='background:#1c1c24;border-radius:20px;padding:16px;text-align:center;border:1px solid #333'>
<h3 style='color:white;margin:0'>{st.session_state.room}</h3>
<p style='color:#10b981;margin:4px'>● TRANSLATOR LIVE</p>
</div>
""", unsafe_allow_html=True)

st.write("")
# Language Selection - Nuvvu anukunna Button
st.markdown("#### 🌐 Language Button (Your Idea)")
col1, col2 = st.columns(2)
with col1:
    my_lang_label = st.selectbox("Nenu Vinedi / I hear in:", list(LANGS.keys()), index=0)
    st.session_state.my_lang = LANGS[my_lang_label]
with col2:
    other_lang_label = st.selectbox("Avatali vallu / Other person:", list(LANGS.keys()), index=1)
    st.session_state.other_lang = LANGS[other_lang_label]

st.success(f"Mode: Other person speaks **{other_lang_label}** -> You hear **{my_lang_label}** | You speak {my_lang_label} -> They hear {other_lang_label}")

st.write("### 🎙️ START nokki Matladu")

# WebRTC Call
webrtc_streamer(
    key=f"trans-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": False, "audio": True},
    async_processing=False,
)

st.divider()
# Translation Display Area - Nee Point No. 6
st.markdown("#### 📝 Live Translated Text (For Clarity)")
st.caption("Real-time lo manam Whisper + Google Translate kaluputham - ippudu demo transcript:")

# Demo Translation Logic (MVP - Next step lo real STT connect chestham)
user_text = st.text_input("Nuvvu matladindi type chey (Demo - tarvata auto STT):", placeholder="Ex: Namaste, ela unnaru?")
if user_text:
    # Simple demo mapping - nee backend translation_service.py laaga
    from deep_translator import GoogleTranslator
    try:
        translated = GoogleTranslator(source=st.session_state.my_lang, target=st.session_state.other_lang).translate(user_text)
        st.session_state.translated = translated
    except:
        translated = f"[{st.session_state.other_lang}] {user_text} (translated)"

    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"**Original ({my_lang_label}):**\n\n{user_text}")
    with c2:
        st.markdown(f"**Translated ({other_lang_label}):**\n\n:green[**{st.session_state.translated}**]")
    
    # TTS - Translated voice play
    try:
        from gtts import gTTS
        import base64, io
        tts = gTTS(text=st.session_state.translated, lang=st.session_state.other_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        st.audio(f"data:audio/mp3;base64,{b64}", format="audio/mp3")
        st.caption("🔊 Translated voice - Other person ki ila vinipistundi")
    except:
        st.warning("TTS kosam gTTS install avvali")

st.divider()
if st.button("📞 End Call", use_container_width=True):
    st.session_state.room=None; st.rerun()
