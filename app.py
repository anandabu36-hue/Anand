import streamlit as st
from sarvamai import SarvamAI
from supabase import create_client
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os, time, uuid, base64, av
import numpy as np

# --- SECRETS ---
try:
    API_KEY = st.secrets["SARVAM_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("🔑 Secrets missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

RTC_CONFIG = RTCConfiguration({"iceServers": [
    {"urls": ["stun:stun.l.google.com:19302"]},
    {"urls": ["stun:stun1.l.google.com:19302"]},
]})

st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu","buffer":[],"last_speech":0,"is_speaking":False,"sending":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login"):
        pwd=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data", exist_ok=True)

# --- ROOM ---
if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator - LIVE CALL</h2>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call", use_container_width=True, type="primary"):
            code=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=code
            supabase.table("broadcasts").insert({"room_id":code,"sender_id":"SYSTEM","text":"Room created","src_lang":"en-IN","src_name":"System"}).execute()
            st.rerun()
    with c2:
        with st.form("join"):
            rc=st.text_input("Room Code")
            if st.form_submit_button("Join"):
                rcc=rc.upper().strip()
                if not rcc.startswith("ANAND-"): st.error("Invalid! ANAND-XXXXX")
                else:
                    res=supabase.table("broadcasts").select("room_id").eq("room_id", rcc).limit(1).execute()
                    if not res.data: st.error("Room Not Found!")
                    else: st.session_state.room=rcc; st.rerun()
    st.stop()

# CSS
st.markdown("""
<style>
.block-container{max-width:420px!important}
.stApp{background:#0a0a0f!important}
.call-header{background:linear-gradient(180deg,#1c1c24,#111115);border-radius:24px;padding:20px;text-align:center;border:1px solid #222}
.timer{color:#10b981;font-weight:700}
.control-label{color:#9ca3af;font-size:11px;text-align:center;margin-top:4px}
.banner{background:linear-gradient(90deg,#10b98122,#667eea22);border:1px solid #10b98144;border-radius:12px;padding:10px;text-align:center;color:#10b981;font-weight:600;margin:12px 0}
.live-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;animation:blink 1s infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0.3}100%{opacity:1}}
</style>
""", unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

st.markdown(f"""
<div class='call-header'>
<h3 style='color:white'>{st.session_state.room}</h3>
<p style='color:#888'>ID: {st.session_state.my_id} • <span class='live-dot'></span> Live</p>
</div>
""", unsafe_allow_html=True)

# --- ONLY I LISTEN - NO I SPEAK ---
st.markdown(f"<div class='banner'>🌐 Auto-Detect → {st.session_state.my_listen} (I Speak Removed)</div>", unsafe_allow_html=True)
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha / I Listen ONLY:", ["Telugu","Hindi","Tamil","English"], 0)

# Dialer buttons
r1c1,r1c2,r1c3=st.columns(3)
with r1c1: st.button("📝",key="a1"); st.markdown("<div class='control-label'>Notes</div>", unsafe_allow_html=True)
with r1c2: 
    if st.button("➕",key="a2"): st.toast(f"Invite: {st.session_state.room}")
    st.markdown("<div class='control-label'>Add call</div>", unsafe_allow_html=True)
with r1c3: st.button("🔇",key="a3"); st.markdown("<div class='control-label'>Mute</div>", unsafe_allow_html=True)
r2c1,r2c2,r2c3=st.columns(3)
with r2c1: st.button("🌐",key="lang",disabled=True); st.markdown("<div class='control-label' style='color:#10b981!important'>Language ON</div>", unsafe_allow_html=True)
with r2c2: st.button("📹",key="a5"); st.markdown("<div class='control-label'>Video</div>", unsafe_allow_html=True)
with r2c3: st.button("⏸️",key="a6"); st.markdown("<div class='control-label'>Hold</div>", unsafe_allow_html=True)
r3c1,r3c2,r3c3=st.columns(3)
with r3c1: st.button("⌨️",key="a7"); st.markdown("<div class='control-label'>Keypad</div>", unsafe_allow_html=True)
with r3c2: 
    if st.button("📞",key="end"): st.session_state.room=None; st.rerun()
    st.markdown("<div class='control-label' style='color:#ef4444'>End call</div>", unsafe_allow_html=True)
with r3c3: st.button("🔊",key="a9"); st.markdown("<div class='control-label'>Speaker</div>", unsafe_allow_html=True)

st.divider()

# --- CONTINUOUS MIC - NO OFF BUTTON NEEDED ---
st.markdown("### 🎙️ LIVE Mic - Matladuthu undu, auto translate avuthundi")

def process_and_send():
    if st.session_state.sending or len(st.session_state.buffer)<8: return
    st.session_state.sending=True
    try:
        # Concatenate buffer (48k -> 16k)
        all_audio = np.concatenate(st.session_state.buffer)
        st.session_state.buffer=[]; st.session_state.is_speaking=False
        # Downsample 48k to 16k
        resampled = all_audio[::3]
        wav_path=f"room_data/live_{st.session_state.my_id}_{int(time.time())}.wav"
        import wave
        with wave.open(wav_path,'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
            wf.writeframes(resampled.astype(np.int16).tobytes())
        with open(wav_path,"rb") as f:
            # AUTO LANGUAGE - no language_code, auto detect
            stt = client.speech_to_text.transcribe(file=f, model="saaras:v3")
            orig = getattr(stt,'transcript','') or ''
        if orig and len(orig.strip())>2:
            st.toast(f"You: {orig}")
            supabase.table("broadcasts").insert({
                "room_id": st.session_state.room,
                "sender_id": st.session_state.my_id,
                "text": orig,
                "src_lang": "auto",
                "src_name": "Auto"
            }).execute()
    except Exception as e:
        st.write(f"STT: {e}")
    finally:
        st.session_state.sending=False

ctx = webrtc_streamer(
    key=f"live-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":{"echoCancellation":True,"noiseSuppression":True,"autoGainControl":True}},
    audio_receiver_size=4096,
    async_processing=True,
)

if ctx and ctx.state.playing:
    st.success("🟢 LIVE - Matladu, aapaku! Auto send avuthundi")
    if ctx.audio_receiver:
        try:
            frames = ctx.audio_receiver.get_frames(timeout=1)
            for fr in frames:
                arr = fr.to_ndarray()
                pcm = arr.mean(axis=0) if arr.ndim==2 else arr.flatten()
                energy = np.sqrt(np.mean(pcm.astype(float)**2))
                if energy>100: # speaking
                    st.session_state.last_speech=time.time()
                    st.session_state.is_speaking=True
                    st.session_state.buffer.append(pcm)
                elif st.session_state.is_speaking:
                    st.session_state.buffer.append(pcm)
            # Auto send after 1.8 sec silence - CONTINUOUS!
            if st.session_state.is_speaking and (time.time()-st.session_state.last_speech)>1.8 and len(st.session_state.buffer)>8:
                process_and_send()
                st.rerun()
        except: pass
else:
    st.warning("👇 START nokki mic ALLOW chey - tarvata matladuthu undu")

st.divider()

@st.fragment(run_every=1)
def live_incoming():
    st.markdown(f"### 🔊 Live Incoming - {st.session_state.my_listen} lo (Auto)")
    try:
        res=supabase.table("broadcasts").select("*").eq("room_id", st.session_state.room).neq("sender_id", st.session_state.my_id).neq("sender_id","SYSTEM").order("created_at", desc=True).limit(2).execute()
        if not res.data:
            st.info("Waiting for other...")
            return
        for r in res.data:
            orig=r["text"]; tgt=lang_map[st.session_state.my_listen]
            cache=f"room_data/inc_{st.session_state.my_id}_{r['id']}.wav"
            txt_cache=cache.replace(".wav",".txt")
            if not os.path.exists(cache):
                trans = client.text.translate(input=orig, source_language_code="auto", target_language_code=tgt, model="mayura:v1")
                translated=getattr(trans,'translated_text',orig)
                open(txt_cache,"w",encoding="utf-8").write(f"{orig} -> {translated}")
                try: tts=client.text_to_speech.convert(text=translated, target_language_code=tgt, model="bulbul:v3")
                except: tts=client.text_to_speech.convert(text=translated, language_code=tgt, model="bulbul:v3")
                data=base64.b64decode(tts.audios[0]); open(cache,"wb").write(data)
            if os.path.exists(cache):
                info=open(txt_cache,"r",encoding="utf-8").read() if os.path.exists(txt_cache) else orig
                st.markdown(f"<div style='background:#1c1c24;padding:10px;border-radius:12px;border-left:4px solid #10b981'>👤 {r['sender_id']}: {info}</div>", unsafe_allow_html=True)
                st.audio(cache, autoplay=True)
    except Exception as e: st.write(e)

live_incoming()
