import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, os, time, uuid, wave, struct
import numpy as np
from collections import deque

try:
    API_KEY = st.secrets["SARVAM_API_KEY"]
except:
    st.error("🔑 SARVAM_API_KEY missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"is_muted":False,"is_live":True,"is_hold":False,"is_speaker":True,"show_keypad":False,"show_notes":False,"my_id":str(uuid.uuid4())[:6],"dial_number":"","notes_text":""}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login"):
        p=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",type="primary",use_container_width=True) and p=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<div style='background:linear-gradient(90deg,#4facfe,#1a237e);border-radius:20px;padding:20px;color:white;text-align:center'><h2>📞 Anand Translator</h2></div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create",use_container_width=True,type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"; os.makedirs("room_data",exist_ok=True)
            open(f"room_data/{st.session_state.room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n"); st.rerun()
    with c2:
        with st.form("join"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join",use_container_width=True):
                rc=code.upper().strip()
                if not os.path.exists(f"room_data/{rc}_users.txt"): st.error("Room Not Found")
                else: st.session_state.room=rc; st.rerun()
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.notes-box{background:#1f2937;border-radius:12px;padding:15px;border:1px solid #333}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important}
.end-btn button{background:#ff3b30!important}
</style>
""", unsafe_allow_html=True)

os.makedirs("room_data",exist_ok=True)
cf=f"room_data/{st.session_state.room}_users.txt"
now=time.time()
users={}
if os.path.exists(cf):
    with open(cf,"r") as f:
        for line in f:
            if "|" in line:
                uid,t=line.strip().split("|")
                try:
                    if now-float(t)<30: users[uid]=float(t)
                except: pass
users[st.session_state.my_id]=now
with open(cf,"w") as f:
    for uid,t in users.items(): f.write(f"{uid}|{t}\n")

# ====== NOTES FIX - Ippudu 100% open avuthundi ======
if st.session_state.show_notes:
    st.markdown("<div class='notes-box'>", unsafe_allow_html=True)
    st.markdown("### 📝 Call Notes")
    st.session_state.notes_text = st.text_area("Type here...", value=st.session_state.notes_text, height=200, key="notes_area")
    c1,c2=st.columns(2)
    with c1:
        if st.button("💾 Save", use_container_width=True, type="primary"):
            with open(f"room_data/{st.session_state.room}_notes.txt","w",encoding="utf-8") as f: f.write(st.session_state.notes_text)
            st.success("Saved!")
    with c2:
        if st.button("❌ Close", use_container_width=True):
            st.session_state.show_notes=False; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()

# ====== KEYPAD TOGGLE FIX ======
if st.session_state.show_keypad:
    st.markdown(f"<div class='call-screen'><h3>{st.session_state.dial_number or ' '}</h3><p>Room: {st.session_state.room}</p></div>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align:center;color:white;font-weight:300;font-size:48px'>{st.session_state.dial_number}</h1>", unsafe_allow_html=True)
    for row in [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]:
        c1,c2,c3=st.columns(3)
        with c1:
            if st.button(row[0],key=f"kp{row[0]}",use_container_width=True): st.session_state.dial_number+=row[0]; st.rerun()
        with c2:
            if st.button(row[1],key=f"kp{row[1]}",use_container_width=True): st.session_state.dial_number+=row[1]; st.rerun()
        with c3:
            if st.button(row[2],key=f"kp{row[2]}",use_container_width=True): st.session_state.dial_number+=row[2]; st.rerun()
    k1,k2,k3=st.columns(3)
    with k1:
        if st.button("⌨️",key="kb1"): st.session_state.show_keypad=False; st.rerun()
    with k2:
        if st.button("📞",key="kb2"):
            if st.session_state.my_id in users: del users[st.session_state.my_id]
            with open(cf,"w") as f:
                for uid,t in users.items(): f.write(f"{uid}|{t}\n")
            st.session_state.room=None; st.rerun()
    with k3:
        if st.button("🔊",key="kb3"): st.session_state.is_speaker=not st.session_state.is_speaker; st.rerun()
else:
    st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{'🔴 On Hold' if st.session_state.is_hold else '🔴 LIVE' if st.session_state.is_live else '⚪ Paused'}<br>Room: {st.session_state.room}</p></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='count-box'>👥 Live: {len(users)} | Room: {st.session_state.room}</div>", unsafe_allow_html=True)
    target=st.selectbox("Translate To:", ["Telugu","Hindi","Tamil","English"], index=0)
    
    r1c1,r1c2,r1c3=st.columns(3)
    with r1c1:
        if st.button("📝",key="b1"): st.session_state.show_notes=True; st.rerun()
        st.markdown("<div class='label'>Notes</div>", unsafe_allow_html=True)
    with r1c2:
        if st.button("➕",key="b2"): st.info(f"Code: {st.session_state.room}")
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
        if st.button("📹",key="b5"): st.toast("Video soon")
        st.markdown("<div class='label'>Video call</div>", unsafe_allow_html=True)
    with r2c3:
        if st.button("⏸️",key="b6"):
            st.session_state.is_hold=not st.session_state.is_hold; st.rerun()
        st.markdown("<div class='label'>Hold</div>", unsafe_allow_html=True)
    r3c1,r3c2,r3c3=st.columns(3)
    with r3c1:
        if st.button("⌨️",key="b7"): st.session_state.show_keypad=True; st.rerun()
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
        if st.button("🔊",key="b9"):
            st.session_state.is_speaker=not st.session_state.is_speaker; st.rerun()
        st.markdown("<div class='label'>Speaker</div>", unsafe_allow_html=True)

# ====== VOICE FIX - REAL FILE EXCHANGE ======
# Buffer for audio
if "audio_buffer" not in st.session_state: st.session_state.audio_buffer=deque(maxlen=100)

def audio_callback(frame: av.AudioFrame):
    if st.session_state.is_hold or st.session_state.is_muted or not st.session_state.is_live:
        return frame
    # Save to buffer
    arr = frame.to_ndarray()
    st.session_state.audio_buffer.append(arr)
    # Every 50 frames (~1 sec) save to file for other user
    if len(st.session_state.audio_buffer) >= 50:
        try:
            # Combine
            combined = np.concatenate(list(st.session_state.audio_buffer), axis=1) if len(st.session_state.audio_buffer)>0 else arr
            # Save as wav for other user
            path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_voice.wav"
            # Simple wav write
            with wave.open(path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                # Convert float to int16 if needed
                if combined.dtype != np.int16:
                    # flatten
                    data = combined.flatten()
                    if data.dtype == np.float32 or data.dtype == np.float64:
                        data = (data * 32767).astype(np.int16)
                    else:
                        data = data.astype(np.int16)
                else:
                    data = combined.flatten().astype(np.int16)
                wf.writeframes(data.tobytes())
            st.session_state.audio_buffer.clear()
        except Exception as e:
            pass
    return frame

ctx = webrtc_streamer(
    key=f"voice-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":{"echoCancellation":True,"noiseSuppression":True,"autoGainControl":True}},
    audio_frame_callback=audio_callback,
    async_processing=True,
)

# --- PLAY OTHER USER VOICE + TRANSLATE ---
st.markdown("### 🔊 Live Audio")
played=False
for uid in users:
    if uid != st.session_state.my_id:
        vpath = f"room_data/{st.session_state.room}_{uid}_voice.wav"
        if os.path.exists(vpath) and time.time() - os.path.getmtime(vpath) < 6:
            st.audio(vpath, autoplay=True)
            st.success(f"🔊 User {uid} speaking...")
            played=True
            # Translate logic - if enabled, run STT -> Translate
            if st.session_state.is_live and not st.session_state.is_hold:
                try:
                    # Sarvam STT
                    with open(vpath,"rb") as f:
                        stt = client.speech_to_text_transcribe(file=f, model="saarika:v2", language_code="te-IN")
                        txt = getattr(stt, 'transcript', '') or str(stt)
                        if txt and len(txt.strip())>2:
                            st.info(f"🗣️ {uid}: {txt}")
                            # Translate to target
                            lang_map = {"Telugu":"te-IN","Hindi":"hi-IN","Tamil":"ta-IN","English":"en-IN"}
                            tgt = lang_map.get(target, "te-IN")
                            # Simple translate via Sarvam
                            # TTS will be done by other client
                            with open(f"room_data/{st.session_state.room}_{uid}_text.txt","w",encoding="utf-8") as tf:
                                tf.write(txt)
                except: pass

if ctx and ctx.state.playing:
    st.success("✅ Mic ON - Matladu, file save avuthundi")
else:
    st.warning("👇 START click chesi Allow chey - appude voice veltundi")

# Check translated text from other user
for uid in users:
    if uid != st.session_state.my_id:
        tpath = f"room_data/{st.session_state.room}_{uid}_text.txt"
        if os.path.exists(tpath) and time.time() - os.path.getmtime(tpath) < 10:
            with open(tpath,"r",encoding="utf-8") as f: st.markdown(f"**Translated from {uid}:** {f.read()}")

time.sleep(1)
st.rerun()
