import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration, AudioProcessorBase
from supabase import create_client
import os, time, uuid, base64, wave, av
import numpy as np

API_KEY = st.secrets["SARVAM_API_KEY"]
SUPA_URL = st.secrets["SUPABASE_URL"]
SUPA_KEY = st.secrets["SUPABASE_KEY"]

client = SarvamAI(api_subscription_key=API_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

st.set_page_config(page_title="Anand Live Call", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_speak":"Hindi","my_listen":"Telugu","audio_buffer":[]}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data",exist_ok=True)

if not st.session_state.room:
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call",use_container_width=True,type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"; st.rerun()
    with c2:
        with st.form("join"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join"):
                st.session_state.room=code.upper().strip(); st.rerun()
    st.stop()

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.write(f"🔴 LIVE ROOM: {st.session_state.room} | ID: {st.session_state.my_id}")

c1,c2=st.columns(2)
with c1: st.session_state.my_speak=st.selectbox("I Speak", ["Hindi","Telugu","Tamil","English"], 0)
with c2: st.session_state.my_listen=st.selectbox("I Listen", ["Telugu","Hindi","Tamil","English"], 1)

# FIX: AudioProcessor - no more queue overflow
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.buffer = []
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        pcm = frame.to_ndarray()
        # mono mix
        mono = pcm.mean(axis=0) if pcm.ndim==2 else pcm.flatten()
        # store in session
        st.session_state.audio_buffer.append(mono)
        return frame

ctx = webrtc_streamer(
    key=f"live-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":{"echoCancellation":True,"noiseSuppression":True,"autoGainControl":True}},
    audio_processor_factory=AudioProcessor,
    async_processing=True,
)

# LIVE AUTO SEND - Every 4 seconds whatever you spoke
if ctx and ctx.state.playing:
    st.success(f"🟢 Mic ON - {len(st.session_state.audio_buffer)} chunks collected | Auto translate every 4 sec")
    
    if len(st.session_state.audio_buffer) > 20 and (time.time() % 4 < 0.5): # every 4 sec
        try:
            all_audio = np.concatenate(st.session_state.audio_buffer)
            st.session_state.audio_buffer = [] # clear
            
            if len(all_audio) < 16000: # <0.33 sec ignore
                pass
            else:
                # 48k -> 16k
                resampled = all_audio[::3]
                wav=f"room_data/live_{st.session_state.my_id}.wav"
                with wave.open(wav,'wb') as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
                    wf.writeframes(resampled.astype(np.int16).tobytes())
                with open(wav,"rb") as f:
                    stt=client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code=lang_map[st.session_state.my_speak])
                    orig=getattr(stt,'transcript','')
                if orig and len(orig.strip())>2:
                    supabase.table("broadcasts").insert({"room_id":st.session_state.room,"room_code":st.session_state.room,"sender_id":st.session_state.my_id,"text":orig,"src_lang":lang_map[st.session_state.my_speak],"src_name":st.session_state.my_speak}).execute()
                    st.toast(f"Sent LIVE: {orig}")
        except Exception as e:
            st.error(f"Live STT Error: {e}")
else:
    st.warning("Click START and ALLOW mic - keep START ON")

st.divider()

# LIVE INCOMING - 1 sec polling = phone call feel
@st.fragment(run_every=1)
def live_incoming():
    try:
        res=supabase.table("broadcasts").select("*").eq("room_id",st.session_state.room).neq("sender_id",st.session_state.my_id).order("created_at",desc=True).limit(1).execute()
        if not res.data:
            st.caption("Waiting for other phone... same room code lo vere phone join avvali")
            return
        r=res.data[0]
        tgt=lang_map[st.session_state.my_listen]
        src=r["src_lang"]
        orig=r["text"]
        translated = orig if src==tgt else getattr(client.text.translate(input=orig, source_language_code=src, target_language_code=tgt, model="mayura:v1"),'translated_text',orig)
        
        st.markdown(f"### 🔊 {r['src_name']} -> {st.session_state.my_listen}: {translated}")
        st.caption(f"Original ({r['sender_id']}): {orig}")

        fpath=f"room_data/live_play_{r['id']}.wav"
        if not os.path.exists(fpath):
            tts=client.text_to_speech.convert(text=translated, target_language_code=tgt, model="bulbul:v3")
            open(fpath,"wb").write(base64.b64decode(tts.audios[0]))
        st.audio(fpath, autoplay=True)
    except Exception as e:
        st.write(f"{e}")

live_incoming()

if st.button("End Call"): st.session_state.room=None; st.session_state.audio_buffer=[]; st.rerun()
