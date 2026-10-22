import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, os, time, uuid
import numpy as np

try:
    API_KEY = st.secrets["SARVAM_API_KEY"]
except:
    st.error("🔑 API Key missing! Secrets lo add chey"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

if "auth" not in st.session_state: st.session_state.auth=False
if "room" not in st.session_state: st.session_state.room=None
if "is_muted" not in st.session_state: st.session_state.is_muted=False
if "is_live" not in st.session_state: st.session_state.is_live=False
if "my_id" not in st.session_state: st.session_state.my_id=str(uuid.uuid4())[:6]

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<div style='background:linear-gradient(90deg,#4facfe,#1a237e);border-radius:20px;padding:20px;color:white;text-align:center'><h2>📞 Anand Translator</h2></div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create",use_container_width=True,type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            os.makedirs("room_data",exist_ok=True)
            open(f"room_data/{st.session_state.room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n")
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join",use_container_width=True):
                rc=code.upper().strip()
                path=f"room_data/{rc}_users.txt"
                if not os.path.exists(path):
                    st.error(f"Room {rc} Not Found!")
                else:
                    st.session_state.room=rc; st.rerun()
    st.stop()

# --- NEE OLD UI DESIGN YELA UNDO ALAGE ---
st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.lang-box{background:#1f2937;border-radius:14px;padding:14px;margin:12px 0}
.stButton>button{background:#2c2c2e!important;width:78px!important;height:78px!important;border-radius:50%!important;border:none!important;color:white!important;font-size:26px!important;margin:0 auto!important;display:block!important}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important;margin-top:6px!important}
.end-btn button{background:#ff3b30!important}
</style>
""", unsafe_allow_html=True)

# --- LIVE COUNT SYNC ---
os.makedirs("room_data",exist_ok=True)
cf=f"room_data/{st.session_state.room}_users.txt"
now=time.time()
users={}
if os.path.exists(cf):
    with open(cf,"r") as f:
        for line in f:
            if "|" in line:
                uid, t = line.strip().split("|")
                try:
                    if now - float(t) < 30:
                        users[uid]=float(t)
                except: pass
users[st.session_state.my_id]=now
with open(cf,"w") as f:
    for uid,t in users.items(): f.write(f"{uid}|{t}\n")
count=len(users)

st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{'🔇 Muted' if st.session_state.is_muted else '🔴 LIVE ON' if st.session_state.is_live else '⚪ Paused'}<br>Room: {st.session_state.room}</p></div>", unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live in Room: {count} Joined • Room: {st.session_state.room}</div>", unsafe_allow_html=True)

target_lang=st.selectbox("Translate To:", ["Telugu","Hindi","Tamil","English"], index=0)

# --- 9 BUTTONS - NEE PHOTO LO UNNATTI ANNI ---
r1c1,r1c2,r1c3=st.columns(3)
with r1c1: 
    if st.button("📝",key="b1"): st.toast("Notes opened")
    st.markdown("<div class='label'>Notes</div>", unsafe_allow_html=True)
with r1c2: 
    if st.button("➕",key="b2"): st.toast(f"Code: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>", unsafe_allow_html=True)
with r1c3: 
    if st.button("🔇" if not st.session_state.is_muted else "🎙️",key="b3"):
        st.session_state.is_muted=not st.session_state.is_muted; st.rerun()
    st.markdown("<div class='label'>Mute</div>", unsafe_allow_html=True)

r2c1,r2c2,r2c3=st.columns(3)
with r2c1: 
    if st.button("🔴" if st.session_state.is_live else "⚪",key="b4"):
        st.session_state.is_live=not st.session_state.is_live; st.rerun()
    st.markdown("<div class='label'>Translate ON</div>", unsafe_allow_html=True)
with r2c2: 
    if st.button("📹",key="b5"): st.toast("Video - Coming soon")
    st.markdown("<div class='label'>Video</div>", unsafe_allow_html=True)
with r2c3: 
    if st.button("⏸️",key="b6"): st.toast("Hold")
    st.markdown("<div class='label'>Hold</div>", unsafe_allow_html=True)

r3c1,r3c2,r3c3=st.columns(3)
with r3c1: 
    if st.button("⌨️",key="b7"): st.toast("Keypad")
    st.markdown("<div class='label'>Keypad</div>", unsafe_allow_html=True)
with r3c2: 
    st.markdown('<div class="end-btn">', unsafe_allow_html=True)
    if st.button("📞",key="b8"): 
        if st.session_state.my_id in users: del users[st.session_state.my_id]
        with open(cf,"w") as f:
            for uid,t in users.items(): f.write(f"{uid}|{t}\n")
        st.session_state.room=None; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div class='label'>End call</div>", unsafe_allow_html=True)
with r3c3: 
    if st.button("🔊",key="b9"): st.toast("Speaker ON")
    st.markdown("<div class='label'>Speaker</div>", unsafe_allow_html=True)

st.divider()
st.markdown(f"#### 📞 Room: {st.session_state.room} | 👥 {count} Live")

# --- VOICE FIX - IDDARIKI VINAPADALI ---
def audio_callback(frame: av.AudioFrame):
    if st.session_state.is_muted:
        # Mute ayithe silent
        arr = np.zeros((frame.samples, frame.layout.nb_channels), dtype=np.int16)
        return av.AudioFrame.from_ndarray(arr, layout=frame.layout.name)
    # Live lo unte voice return chey - iddaru vinagalaru
    return frame

webrtc_streamer(
    key=f"call-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    audio_frame_callback=audio_callback,
    async_processing=True,
)

# AUTO REFRESH FOR COUNT + VOICE SYNC
time.sleep(3)
st.rerun()
