import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import uuid

st.set_page_config(page_title="Anand Live Translator", layout="centered")

# Clean STUN only - No TURN crash - logs lo error povadaniki
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

LANGS = {
    "Telugu - తెలుగు": "te",
    "Hindi - हिंदी": "hi", 
    "English": "en",
    "Tamil - தமிழ்": "ta",
    "Kannada - ಕನ್ನಡ": "kn"
}

for k,v in {"auth":False,"room":None,"my_lang":"te","other_lang":"hi"}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>🔒 Anand Translator</h2>", unsafe_allow_html=True)
    with st.form("a"):
        p=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary") and p=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Live Phone Call Translator</h2><p style='text-align:center;color:#888'>Language Button - Your Idea</p>", unsafe_allow_html=True)
    st.info("Caller Hindi -> You hear Telugu | You Telugu -> Caller hears Hindi")
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

st.markdown(f"<div style='background:#1c1c24;border-radius:20px;padding:16px;text-align:center;border:1px solid #333'><h3 style='color:white'>{st.session_state.room}</h3><p style='color:#10b981'>● TRANSLATOR LIVE</p></div>", unsafe_allow_html=True)

st.write("")
st.markdown("#### 🌐 Language Button - Your Concept")
col1, col2 = st.columns(2)
with col1:
    my_label = st.selectbox("Nenu Vinedi:", list(LANGS.keys()), index=0)
    st.session_state.my_lang = LANGS[my_label]
with col2:
    other_label = st.selectbox("Other Person:", list(LANGS.keys()), index=1)
    st.session_state.other_lang = LANGS[other_label]

st.success(f"{other_label} -> {my_label} | {my_label} -> {other_label}")

st.write("### 🎙️ START nokki Matladu")
webrtc_streamer(
    key=f"trans-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": False, "audio": True},
    async_processing=False, # No frame drop - Real phone clarity
)

st.divider()
st.markdown("#### 📝 Live Translation Demo")
user_text = st.text_input("Type to test translation (Next: auto STT):", placeholder="Ex: Namaste")
if user_text:
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source=st.session_state.my_lang, target=st.session_state.other_lang).translate(user_text)
        st.write(f"**Original ({my_label}):** {user_text}")
        st.success(f"**Translated ({other_label}):** {translated}")
        from gtts import gTTS
        import base64, io
        tts = gTTS(text=translated, lang=st.session_state.other_lang)
        fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        st.audio(f"data:audio/mp3;base64,{b64}", format="audio/mp3")
    except Exception as e:
        st.error(f"Install deep-translator gtts: {e}")

if st.button("📞 End Call", use_container_width=True):
    st.session_state.room=None; st.rerun()
