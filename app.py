import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration, AudioProcessorBase
import uuid
import av
import numpy as np

st.set_page_config(page_title="Anand Voice Call HD", layout="centered")

# TURN + STUN - WiFi + Data lo kuda work avvadaniki
RTC_CONFIG = RTCConfiguration({"iceServers": [
    {"urls": ["stun:stun.l.google.com:19302"]},
    {"urls": ["stun:stun1.l.google.com:19302"]},
    {"urls": ["stun:stun2.l.google.com:19302"]},
    {
        "urls": ["turn:openrelay.metered.ca:80"],
        "username": "openrelayproject",
        "credential": "openrelayproject"
    },
    {
        "urls": ["turn:openrelay.metered.ca:443"],
        "username": "openrelayproject",
        "credential": "openrelayproject"
    },
]})

# HD Processor - No blur filter
class HDVoiceProcessor(AudioProcessorBase):
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        return frame

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6]}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>🔒 Anand HD Voice Call</h2>", unsafe_allow_html=True)
    with st.form("login"):
        pwd=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 HD Voice Call - Real Phone Clarity</h2><p style='text-align:center;color:#888'>WiFi + Mobile Data - Both Work</p>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call", use_container_width=True, type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        with st.form("join"):
            code=st.text_input("Room Code (ANAND-XXXXX)")
            if st.form_submit_button("Join", use_container_width=True):
                rc=code.upper().strip()
                if not rc.startswith("ANAND-"): st.error("Format ANAND-XXXXX")
                else: st.session_state.room=rc; st.rerun()
    st.stop()

# UI
st.markdown(f"""
<style>
.block-container{{max-width:400px!important}}
.stApp{{background:#0a0a0f!important}}
.call-card{{background:linear-gradient(180deg,#1c1c24,#111115);border-radius:24px;padding:24px;text-align:center;border:1px solid #222}}
</style>
<div class='call-card'>
<h2 style='color:white'>{st.session_state.room}</h2>
<p style='color:#888'>My ID: {st.session_state.my_id}</p>
<p style='color:#10b981'>● HD LIVE - Real Phone Clarity</p>
<p style='color:#aaa;font-size:12px'>WiFi + Data - Any Network Works</p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.markdown("### 🎙️ START nokki Matladu - Real Phone Laaga")

ctx = webrtc_streamer(
    key=f"hd-voice-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={
        "video": False,
        "audio": {
            "echoCancellation": False,
            "noiseSuppression": False,
            "autoGainControl": False,
            "channelCount": 1,
            "sampleRate": {"ideal": 48000},
            "sampleSize": {"ideal": 16},
            "googEchoCancellation": False,
            "googAutoGainControl": False,
            "googNoiseSuppression": False,
            "googHighpassFilter": False,
        }
    },
    audio_processor_factory=HDVoiceProcessor,
    audio_receiver_size=1024,
    async_processing=True,
)

if ctx.state.playing:
    st.success("🟢 HD LIVE - Crystal Clear! Headset pettukunte real phone kanna better!")
else:
    st.warning("👇 START nokki Mic ALLOW chey")

st.divider()
if st.button("📞 End Call", use_container_width=True):
    st.session_state.room=None; st.rerun()
