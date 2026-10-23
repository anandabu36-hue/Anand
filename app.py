import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from supabase import create_client
import os, time, uuid, base64, wave
import numpy as np

API_KEY = st.secrets["SARVAM_API_KEY"]
SUPA_URL = st.secrets["SUPABASE_URL"]
SUPA_KEY = st.secrets["SUPABASE_KEY"]

client = SarvamAI(api_subscription_key=API_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]},
    ]
})

st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_speak":"Hindi","my_listen":"Telugu","buffer":[],"last_speech":0,"is_speaking":False,"auto_lock":False,"call_start":0}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data",exist_ok=True)

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator - LIVE</h2>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call",use_container_width=True,type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.call_start=time.time()
            st.rerun()
    with c2:
        with st.form("join"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join"):
                st.session_state.room=code.upper().strip()
                st.session_state.call_start=time.time()
                st.rerun()
    st.stop()

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

# UI Header
now=time.time()
dur=int(now-st.session_state.call_start) if st.session_state.call_start else 0
m,s=divmod(dur,60)
st.markdown(f"""
<div style='background:#1c1c24;border-radius:20px;padding:16px;text-align:center'>
<h3>Room {st.session_state.room}</h3>
<p>ID: {st.session_state.my_id} • 🟢 {m:02d}:{s:02d} • Auto Listening ON</p>
</div>
""", unsafe_allow_html=True)

c1,c2=st.columns(2)
with c1: st.session_state.my_speak=st.selectbox("I Speak", ["Hindi","Telugu","Tamil","English"], 0)
with c2: st.session_state.my_listen=st.selectbox("I Listen", ["Telugu","Hindi","Tamil","English"], 1)

# FIXED: SENDONLY + 4096 buffer
ctx = webrtc_streamer(
    key=f"call-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":{"echoCancellation":True,"noiseSuppression":True}},
    audio_receiver_size=4096,
    async_processing=True,
)

def process_buffer():
    if st.session_state.auto_lock or len(st.session_state.buffer)<10: return
    st.session_state.auto_lock=True
    try:
        all_audio=np.concatenate(st.session_state.buffer)
        st.session_state.buffer=[]; st.session_state.is_speaking=False
        # 48k -> 16k for Sarvam
        resampled=all_audio[::3]
        wav=f"room_data/{st.session_state.my_id}_16k.wav"
        with wave.open(wav,'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
            wf.writeframes(resampled.astype(np.int16).tobytes())
        with open(wav,"rb") as f:
            stt=client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code=lang_map[st.session_state.my_speak])
            orig=getattr(stt,'transcript','')
        if orig and len(orig.strip())>1:
            supabase.table("broadcasts").insert({"room_id":st.session_state.room,"room_code":st.session_state.room,"sender_id":st.session_state.my_id,"text":orig,"src_lang":lang_map[st.session_state.my_speak],"src_name":st.session_state.my_speak}).execute()
            st.toast(f"✅ LIVE Sent: {orig}")
    except Exception as e: st.error(f"Send Error: {e}")
    finally: st.session_state.auto_lock=False

if ctx and ctx.state.playing and ctx.audio_receiver:
    st.success("🎙️ Mic ON - Matladu, 2 sec gap = auto send")
    try:
        frames=ctx.audio_receiver.get_frames(timeout=0.5)
        for fr in frames:
            arr=fr.to_ndarray(); pcm=arr.mean(axis=0) if arr.ndim==2 else arr.flatten()
            en=np.sqrt(np.mean(pcm.astype(float)**2))
            if en>80:
                st.session_state.last_speech=time.time(); st.session_state.is_speaking=True
                st.session_state.buffer.append(pcm)
            elif st.session_state.is_speaking:
                st.session_state.buffer.append(pcm)
    except: pass
    if st.session_state.is_speaking and (time.time()-st.session_state.last_speech)>2.0 and len(st.session_state.buffer)>10:
        process_buffer(); st.rerun()
else:
    st.warning("Click START and ALLOW mic")

st.divider()

@st.fragment(run_every=1)
def incoming():
    st.write(f"Incoming - {st.session_state.my_listen} (LIVE Phone Call)")
    try:
        res=supabase.table("broadcasts").select("*").eq("room_id",st.session_state.room).neq("sender_id",st.session_state.my_id).order("created_at",desc=True).limit(1).execute()
        if not res.data:
            st.caption(f"Waiting in {st.session_state.room}... other phone same code join ayithe vastundi")
            return
        r=res.data[0]
        orig=r["text"]; src=r["src_lang"]; src_name=r["src_name"]
        tgt=lang_map[st.session_state.my_listen]
        translated = orig if src==tgt else getattr(client.text.translate(input=orig, source_language_code=src, target_language_code=tgt, model="mayura:v1"),'translated_text',orig)
        st.success(f"👤 {src_name}: {orig} -> {st.session_state.my_listen}: {translated}")
        fpath=f"room_data/live_{r['id']}.wav"
        if not os.path.exists(fpath):
            tts=client.text_to_speech.convert(text=translated, target_language_code=tgt, model="bulbul:v3")
            open(fpath,"wb").write(base64.b64decode(tts.audios[0]))
        st.audio(fpath, autoplay=True)
    except Exception as e: st.error(f"{e}")

incoming()
if st.button("End Call"): st.session_state.room=None; st.rerun()
