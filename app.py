import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, os, time, uuid, base64, glob, wave
import numpy as np

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"is_muted":False,"is_live":True,"is_hold":False,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu","recording":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator</h2>",unsafe_allow_html=True)
    if st.button("Create New Room",type="primary",use_container_width=True):
        st.session_state.room=f"ANAND-{str(uuid.uuid4())[:4].upper()}"
        os.makedirs("room_data",exist_ok=True)
        open(f"room_data/{st.session_state.room}.room","w").write("room")
        st.rerun()
    with st.form("join"):
        code=st.text_input("Room Code")
        if st.form_submit_button("Join",use_container_width=True):
            rc=code.upper().strip()
            os.makedirs("room_data",exist_ok=True)
            if not os.path.exists(f"room_data/{rc}.room") and not os.path.exists(f"room_data/{rc}_users.txt"):
                st.error(f"Room {rc} Not Found!")
            else:
                st.session_state.room=rc; st.rerun()
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.label{color:#a1a1a6!important;font-size:11px!important;text-align:center!important;margin-bottom:15px!important}
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
                    if now-float(t)<40: users[uid]=float(t)
                except: pass
users[st.session_state.my_id]=now
with open(cf,"w") as f:
    for uid,t in users.items(): f.write(f"{uid}|{t}\n")
count=len(users)

st.markdown(f"<div class='call-screen'><h3>Room: {st.session_state.room}</h3><p>👥 Live: {count} | 🔴 LIVE</p></div>",unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.session_state.my_listen=st.selectbox("I Listen:", ["Telugu","Hindi","Tamil","English"], index=["Telugu","Hindi","Tamil","English"].index(st.session_state.my_listen))
st.caption("Nuvvu em matladina auto-detect - START lone record avuthundi")

# --- 9 BUTTONS ---
r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1"): st.session_state.show_notes=not st.session_state.get("show_notes",False)
    st.markdown("<div class='label'>Notes</div>",unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2"): st.info(f"Code: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>",unsafe_allow_html=True)
with r1c3:
    if st.button("🔇",key="b3"): st.session_state.is_muted=not st.session_state.is_muted
    st.markdown("<div class='label'>Mute</div>",unsafe_allow_html=True)
r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("🔴",key="b4"): st.session_state.is_live=not st.session_state.is_live
    st.markdown("<div class='label'>Translate</div>",unsafe_allow_html=True)
with r2c2:
    if st.button("📹",key="b5"): st.toast("Video soon")
    st.markdown("<div class='label'>Video</div>",unsafe_allow_html=True)
with r2c3:
    if st.button("⏸️",key="b6"): st.session_state.is_hold=not st.session_state.is_hold
    st.markdown("<div class='label'>Hold</div>",unsafe_allow_html=True)
r3c1,r3c2,r3c3=st.columns(3)
with r3c1:
    if st.button("⌨️",key="b7"): pass
    st.markdown("<div class='label'>Keypad</div>",unsafe_allow_html=True)
with r3c2:
    if st.button("📞",key="b8"): st.session_state.room=None; st.rerun()
    st.markdown("<div class='label'>End</div>",unsafe_allow_html=True)
with r3c3:
    if st.button("🔊",key="b9"): pass
    st.markdown("<div class='label'>Speaker</div>",unsafe_allow_html=True)

st.divider()

# --- START = MIC + RECORD ON/OFF ---
# Buffer file for live recording
BUFFER_RAW = f"room_data/{st.session_state.room}_{st.session_state.my_id}_live.raw"
META_FILE = f"room_data/{st.session_state.room}_{st.session_state.my_id}_meta.txt"

def audio_callback(frame: av.AudioFrame):
    if st.session_state.is_hold or st.session_state.is_muted or not st.session_state.is_live:
        return frame
    try:
        # Save PCM continuously while START is ON
        arr = frame.to_ndarray()
        # Save meta once
        if not os.path.exists(META_FILE):
            open(META_FILE,"w").write(f"{frame.sample_rate},{frame.layout.name},{arr.shape}")
        with open(BUFFER_RAW,"ab") as f:
            f.write(arr.tobytes())
    except: pass
    return frame

st.markdown("### 🎤 Step 1: START = Record ON, STOP = Record OFF + Sent")
ctx = webrtc_streamer(
    key=f"voice-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    audio_frame_callback=audio_callback,
    async_processing=True,
)

if ctx.state.playing:
    st.success("🔴 Recording... Matladu! Aipoyaka STOP nokku")
    st.session_state.recording = True
else:
    if st.session_state.recording:
        # Just stopped - process buffer
        st.session_state.recording = False
        if os.path.exists(BUFFER_RAW) and os.path.getsize(BUFFER_RAW) > 1000:
            with st.spinner("Processing... Auto-detect & Sending..."):
                try:
                    # Convert raw to wav
                    wav_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
                    # Try to get meta
                    sr = 48000
                    ch = 1
                    if os.path.exists(META_FILE):
                        try:
                            meta = open(META_FILE,"r").read().split(",")
                            sr = int(meta[0])
                        except: pass
                    # Read raw bytes
                    raw_data = open(BUFFER_RAW,"rb").read()
                    # Convert int16 array to wav
                    # Assume mono/stereo detection from array shape
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) # int16
                        wf.setframerate(sr)
                        wf.writeframes(raw_data)
                    
                    # Clear buffer for next
                    os.remove(BUFFER_RAW)
                    if os.path.exists(META_FILE): os.remove(META_FILE)

                    # STT Auto-detect
                    with open(wav_path,"rb") as f:
                        try:
                            stt = client.speech_to_text.transcribe(file=f, model="saaras:v3")
                        except:
                            f.seek(0)
                            stt = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
                        orig = getattr(stt,'transcript','') or str(stt)
                    
                    if orig:
                        st.info(f"You said: {orig}")
                        bfile = f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
                        open(bfile,"w",encoding="utf-8").write(orig)
                        st.success("✅ Sent! Vere phone lo Refresh nokkithe vadiki vinipisthundi")
                except Exception as e:
                    st.error(f"Error: {e}")
                    if os.path.exists(BUFFER_RAW): os.remove(BUFFER_RAW)
        else:
            st.warning("👇 START nokki matladu - STOP nokkithe Sent avuthundi")

# Clear buffer button if stuck
if os.path.exists(BUFFER_RAW):
    if st.button("🗑️ Clear Buffer & Restart"):
        os.remove(BUFFER_RAW)
        if os.path.exists(META_FILE): os.remove(META_FILE)
        st.rerun()

st.divider()
st.markdown(f"### 🔊 Step 2: Incoming - {st.session_state.my_listen} lo")
files=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
files=[f for f in files if "_lang" not in f][:5]
for f in files:
    try:
        if st.session_state.my_id in f: continue
        if time.time()-os.path.getmtime(f)>600: continue
        orig=open(f,"r",encoding="utf-8").read()
        sender=f.split("_")[-1].replace(".txt","")
        tgt=lang_map[st.session_state.my_listen]
        cache=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender}_{int(os.path.getmtime(f))}_{st.session_state.my_listen}.wav"
        cache_txt=cache.replace(".wav",".txt")
        if not os.path.exists(cache):
            with st.spinner(f"Translating to {st.session_state.my_listen}..."):
                trans=client.text.translate(input=orig, source_language_code="auto", target_language_code=tgt, model="mayura:v1")
                tr=getattr(trans,'translated_text',orig)
                open(cache_txt,"w",encoding="utf-8").write(f"{orig} -> {tr}")
                try: tts=client.text_to_speech.convert(text=tr, target_language_code=tgt, speaker="anand", model="bulbul:v3")
                except: tts=client.text_to_speech.convert(text=tr, language_code=tgt, speaker="anand", model="bulbul:v3")
                aud=tts.audios[0] if hasattr(tts,'audios') else None
                if aud:
                    try: data=base64.b64decode(aud)
                    except: data=aud.encode() if isinstance(aud,str) else aud
                    open(cache,"wb").write(data)
        if os.path.exists(cache):
            info=open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig
            st.markdown(f"**From {sender}:** {info}")
            st.audio(cache, autoplay=True)
    except Exception as e: st.error(f"{e}")

if st.button("🔄 Refresh Incoming",use_container_width=True, type="primary"):
    st.rerun()
