import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os, time, uuid, base64, glob, wave
import numpy as np

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)

# FIX: Multiple STUN servers - mobile data lo connect avuthundi
RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]},
        {"urls": ["stun:stun3.l.google.com:19302"]},
    ]
})

st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu","buffer":[],"last_speech":0,"is_speaking":False,"call_start":0,"auto_lock":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock Call",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data",exist_ok=True)

if not st.session_state.room:
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call",use_container_width=True,type="primary"):
            new_room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=new_room
            st.session_state.call_start=time.time()
            open(f"room_data/{new_room}.room","w").write("room")
            open(f"room_data/{new_room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n")
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join Call",use_container_width=True):
                rc=code.upper().strip().replace(" ","")
                if os.path.exists(f"room_data/{rc}.room") or os.path.exists(f"room_data/{rc}_users.txt"):
                    st.session_state.room=rc
                    st.session_state.call_start=time.time()
                    st.rerun()
                else: st.error(f"❌ Room {rc} Not Found!")
    st.stop()

st.markdown("<style>.block-container{max-width:400px!important}.stApp{background:#0a0a0f!important}</style>", unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.write(f"Room: {st.session_state.room} | ID: {st.session_state.my_id}")
st.session_state.my_listen=st.selectbox("I Listen:", ["Telugu","Hindi","Tamil","English"])

# FIXED CONNECTION
ctx = webrtc_streamer(
    key=f"call-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":{"echoCancellation":True,"noiseSuppression":True,"autoGainControl":True}},
    audio_receiver_size=4096,
    async_processing=True,
)

def process_buffer():
    if st.session_state.auto_lock or len(st.session_state.buffer) < 15: return
    st.session_state.auto_lock = True
    try:
        all_audio = np.concatenate(st.session_state.buffer)
        st.session_state.buffer = []; st.session_state.is_speaking = False
        wav_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_{int(time.time())}.wav"
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(48000)
            wf.writeframes(all_audio.astype(np.int16).tobytes())
        with open(wav_path,"rb") as f:
            try: stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
            except: 
                f.seek(0)
                stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
            orig = getattr(stt_res, 'transcript', '') or str(stt_res)
        if orig and len(orig.strip())>1:
            bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
            open(bfile,"w",encoding="utf-8").write(orig)
            st.toast(f"✅ Sent: {orig[:40]}")
    except Exception as e: st.error(f"{e}")
    finally: st.session_state.auto_lock = False

if ctx and ctx.state.playing and ctx.audio_receiver:
    st.success("🟢 Mic ON - Matladu, 2 sec silent aithe auto send")
    try:
        frames = ctx.audio_receiver.get_frames(timeout=0.5)
        for frame in frames:
            arr = frame.to_ndarray()
            pcm = arr.mean(axis=0) if arr.ndim==2 else arr.flatten()
            energy = np.sqrt(np.mean(pcm.astype(float)**2))
            if energy > 300: # threshold taggincha
                st.session_state.last_speech = time.time()
                st.session_state.is_speaking = True
                st.session_state.buffer.append(pcm)
            elif st.session_state.is_speaking:
                st.session_state.buffer.append(pcm)
    except: pass
    if st.session_state.is_speaking and (time.time() - st.session_state.last_speech) > 2.0 and len(st.session_state.buffer) > 15:
        process_buffer(); st.rerun()
else:
    st.warning("Click START and ALLOW mic - Connection error ippudu radu")

# --- INCOMING ---
@st.fragment(run_every=1.5)
def auto_incoming():
    broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
    found=False
    for bfile in broadcasts[:3]:
        try:
            if st.session_state.my_id in bfile: continue
            orig_text=open(bfile,"r",encoding="utf-8").read()
            if not orig_text: continue
            found=True
            tgt_code=lang_map[st.session_state.my_listen]
            cache_audio=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_{int(os.path.getmtime(bfile))}.wav"
            if not os.path.exists(cache_audio):
                trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                translated = getattr(trans_res, 'translated_text', orig_text)
                tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, model="bulbul:v3")
                open(cache_audio,"wb").write(base64.b64decode(tts_res.audios[0]))
                st.write(f"👤 {translated}")
            st.audio(cache_audio, autoplay=True)
        except Exception as e: st.error(f"{e}")
    if not found: st.caption("Waiting...")

auto_incoming()
if st.button("End Call"): st.session_state.room=None; st.rerun()
