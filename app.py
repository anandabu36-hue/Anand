import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import uuid

st.set_page_config(page_title="Anand Voice Call", layout="centered")

RTC_CONFIG = RTCConfiguration({"iceServers": [
    {"urls": ["stun:stun.l.google.com:19302"]},
    {"urls": ["stun:stun1.l.google.com:19302"]},
    {"urls": ["stun:stun2.l.google.com:19302"]},
]})

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6]}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>🔒 Anand Voice Call - Pure</h2>", unsafe_allow_html=True)
    with st.form("login"):
        pwd=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Pure Voice Call</h2><p style='text-align:center'>No Translate - Just Live Voice like Phone</p>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call", use_container_width=True, type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        with st.form("join"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join"):
                rc=code.upper().strip()
                if not rc.startswith("ANAND-"): st.error("Format ANAND-XXXXX")
                else: st.session_state.room=rc; st.rerun()
    st.info("Create chesi code ni vere phone ki share chey. Rendu phones lo same code tho START nokkite iddaru matladukovacchu phone laga.")
    st.stop()

# Phone UI
st.markdown(f"""
<style>
.block-container{{max-width:400px!important}}
.stApp{{background:#0a0a0f!important}}
.call-card{{background:linear-gradient(180deg,#1c1c24,#111115);border-radius:24px;padding:24px;text-align:center;border:1px solid #222}}
</style>
<div class='call-card'>
<h2 style='color:white'>{st.session_state.room}</h2>
<p style='color:#888'>My ID: {st.session_state.my_id}</p>
<p style='color:#10b981'>● LIVE Voice Call - No Translate</p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.markdown("### 🎙️ Step 1: START nokki Mic Allow chey")
st.caption("Rendu phones lo same Room lo START nokkithe iddaru voice lu iddariki live vinipistayi - phone laga")

# THIS IS THE PHONE CALL - SENDRECV
ctx = webrtc_streamer(
    key=f"voice-{st.session_state.room}",  # Same key = same room lo iddaru connect avutharu
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    async_processing=True,
)

if ctx.state.playing:
    st.success("🟢 LIVE - Iddaru matladukondi! Phone call laga")
    st.info("Nuvvu matladithe avathali phone lo direct ga vinipistundi. Translate ledu ippudu - only pure voice.")
else:
    st.warning("👇 START button nokki mic ALLOW chey")

st.divider()
if st.button("📞 End Call", use_container_width=True):
    st.session_state.room=None; st.rerun()
