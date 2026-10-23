import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from supabase import create_client
import os, time, uuid, base64, wave, asyncio
import numpy as np

API_KEY = st.secrets["SARVAM_API_KEY"]
SUPA_URL = st.secrets["SUPABASE_URL"]
SUPA_KEY = st.secrets["SUPABASE_KEY"]

client = SarvamAI(api_subscription_key=API_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Live Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_speak":"Hindi","my_listen":"Telugu","buffer":[],"last_send":0}.items():
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
st.title(f"🔴 LIVE: {st.session_state.room}")
st.caption(f"My ID: {st.session_state.my_id} | Phone call laga matladu - auto translate avuthundi")

c1,c2=st.columns(2)
with c1: st.session_state.my_speak=st.selectbox("I Speak", ["Hindi","Telugu","Tamil","English"], 0)
with c2: st.session_state.my_listen=st.selectbox("I Listen", ["Telugu","Hindi","Tamil","English"], 1)

# LIVE MODE - SENDONLY (no echo) + continuous collecting
ctx = webrtc_streamer(key=f"live-{st.session_state.room}-{st.session_state.my_id}", mode=WebRtcMode.SENDONLY, rtc_configuration=RTC_CONFIG, media_stream_constraints={"video":False,"audio":{"echoCancellation":True,"noiseSuppression":True,"autoGainControl":True}}, audio_receiver_size=512, async_processing=True)

def live_translate_and_send():
    if len(st.session_state.buffer) < 8: return
    try:
        all_audio=np.concatenate(st.session_state.buffer)
        st.session_state.buffer=[] # Clear for next 3 sec
        st.session_state.last_send=time.time()
        
        # 48k -> 16k resample
        resampled = all_audio[::3]
        if len(resampled) < 8000: return # <0.5 sec ignore

        wav=f"room_data/live_{st.session_state.my_id}.wav"
        with wave.open(wav,'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
            wf.writeframes(resampled.astype(np.int16).tobytes())

        with open(wav,"rb") as f:
            stt=client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code=lang_map[st.session_state.my_speak])
            orig=getattr(stt,'transcript','')

        if orig and len(orig.strip())>2:
            # Instant broadcast
            supabase.table("broadcasts").insert({"room_id":st.session_state.room,"sender_id":st.session_state.my_id,"text":orig,"src_lang":lang_map[st.session_state.my_speak],"src_name":st.session_state.my_speak}).execute()
            st.toast(f"You: {orig}")
    except Exception as e:
        print(f"Live error: {e}")

# Continuous VAD - No silence wait, every 3 sec auto send
if ctx and ctx.state.playing and ctx.audio_receiver:
    try:
        frames=ctx.audio_receiver.get_frames(timeout=0.5)
        for fr in frames:
            arr=fr.to_ndarray()
            pcm=arr.mean(axis=0) if arr.ndim==2 else arr.flatten()
            # Add all frames, not just loud
            st.session_state.buffer.append(pcm)
    except: pass

    # Every 3 seconds, auto translate whatever you spoke
    if len(st.session_state.buffer) > 25 and (time.time() - st.session_state.last_send) > 3.0:
        live_translate_and_send()
        st.rerun()
    
    st.success(f"🟢 LIVE - Mic ON | Speaking... next translate in {max(0, 3 - int(time.time()-st.session_state.last_send))}s")
else:
    st.warning("Click START -> Allow Mic -> Keep it ON, don't press STOP")

st.divider()

# LIVE INCOMING - Poll every 1 sec for instant
@st.fragment(run_every=1)
def live_incoming():
    try:
        res=supabase.table("broadcasts").select("*").eq("room_id",st.session_state.room).neq("sender_id",st.session_state.my_id).order("created_at",desc=True).limit(1).execute()
        if not res.data: return
        r=res.data[0]
        # Only play if message is within last 10 seconds - LIVE feel
        # created_at check
        tgt=lang_map[st.session_state.my_listen]
        if r["src_lang"] == tgt:
            translated = r["text"]
        else:
            translated = getattr(client.text.translate(input=r["text"], source_language_code=r["src_lang"], target_language_code=tgt, model="mayura:v1"),'translated_text',r["text"])
        
        st.markdown(f"### 🔊 {r['src_name']} ({r['sender_id']}): {translated}")
        st.caption(f"Original: {r['text']}")
        
        # Auto TTS and autoplay
        fpath=f"room_data/live_play_{r['id']}.wav"
        if not os.path.exists(fpath):
            tts=client.text_to_speech.convert(text=translated, target_language_code=tgt, model="bulbul:v3")
            open(fpath,"wb").write(base64.b64decode(tts.audios[0]))
        st.audio(fpath, autoplay=True)
    except Exception as e:
        st.write(f"Incoming error: {e}")

live_incoming()

if st.button("End Call"): st.session_state.room=None; st.rerun()
