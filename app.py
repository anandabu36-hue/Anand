import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import uuid

st.set_page_config(page_title="Anand Live Translator", layout="centered")

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

LANGS = {"Telugu - తెలుగు":"te","Hindi - हिंदी":"hi","English":"en","Tamil - தமிழ்":"ta"}

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
    st.markdown("<h2 style='text-align:center'>📞 Live Translator</h2>", unsafe_allow_html=True)
    st.info("Test: 2 phones lo same code tho join avvali - okkadi phone lo okkadi voice vinipistundi")
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

st.markdown(f"<div style='background:#1c1c24;border-radius:20px;padding:16px;text-align:center'><h3 style='color:white'>{st.session_state.room}</h3><p style='color:#10b981'>● LIVE</p></div>", unsafe_allow_html=True)
st.write("")

# Language Button - Nee Idea
col1, col2 = st.columns(2)
with col1:
    my_label = st.selectbox("Nenu Vinedi:", list(LANGS.keys()), index=0)
    st.session_state.my_lang = LANGS[my_label]
with col2:
    other_label = st.selectbox("Other:", list(LANGS.keys()), index=1)
    st.session_state.other_lang = LANGS[other_label]

st.write("### 🎙️ START nokki Matladu")

# --- ECHO FIX HERE ---
webrtc_streamer(
    key=f"call-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={
        "video": False,
        "audio": {
            "echoCancellation": True,  # ON - echo povadaniki
            "noiseSuppression": True,   # ON
            "autoGainControl": True,    # ON
            "googEchoCancellation": True,
            "googNoiseSuppression": True,
        }
    },
    async_processing=False,
)

st.warning("**Test ela cheyali:**\n1. Phone A lo Create -> ANAND-XXXXX copy\n2. Phone B lo Join -> same code\n3. Rendu phones **vere vere room lo** pettu, leka **Headset pettu**\n4. Appudu na voice nake vinipinchadu, avatala vallaki matrame veltundi")

if st.button("📞 End Call", use_container_width=True):
    st.session_state.room=None; st.rerun()
