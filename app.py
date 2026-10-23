import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import uuid

st.set_page_config(page_title="Anand HD Voice", layout="centered", initial_sidebar_state="collapsed")

# Simple STUN only - No TURN crash
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6]}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>🔒 Anand Voice</h2>", unsafe_allow_html=True)
    with st.form("login"):
        pwd=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Voice Call - Real Clarity</h2>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create", use_container_width=True, type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code ANAND-XXXXX")
            if st.form_submit_button("Join", use_container_width=True):
                rc=code.upper().strip()
                st.session_state.room=rc; st.rerun()
    st.stop()

st.markdown(f"""
<style>
.block-container{{max-width:400px!important}}
.stApp{{background:#0a0a0f!important}}
.card{{background:#1c1c24;border-radius:20px;padding:20px;text-align:center;border:1px solid #333}}
</style>
<div class='card'><h3 style='color:white'>{st.session_state.room}</h3><p style='color:#10b981'>● LIVE</p></div>
""", unsafe_allow_html=True)

st.write("### 🎙️ START nokki Matladu")

# PURE P2P - No Processor - This gives REAL PHONE clarity
webrtc_streamer(
    key=f"voice-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={
        "video": False,
        "audio": {
            "echoCancellation": True,
            "noiseSuppression": True,
            "autoGainControl": True,
        }
    },
    async_processing=False,  # Important - no frame drop
)

st.divider()
if st.button("📞 End Call", use_container_width=True):
    st.session_state.room=None; st.rerun()
