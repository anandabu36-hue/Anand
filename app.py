import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, os, time, uuid, base64, glob, wave

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"], "urls": ["turn:openrelay.metered.ca:80"], "username": "openrelayproject", "credential": "openrelayproject"}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"is_muted":False,"is_live":True,"is_hold":False,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu","was_recording":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<div style='background:linear-gradient(90deg,#4facfe,#1a237e);border-radius:20px;padding:20px;color:white;text-align:center'><h2>📞 Anand Translator</h2><p>Level 2.5 - Auto Real Call</p></div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create",use_container_width=True,type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            os.makedirs("room_data",exist_ok=True)
            open(f"room_data/{st.session_state.room}.room","w").write("room")
            open(f"room_data/{st.session_state.room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n")
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join",use_container_width=True):
                rc=code.upper().strip().replace(" ","")
                os.makedirs("room_data",exist_ok=True)
                st.session_state.room=rc; st.rerun()
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important;margin-top:6px!important}
.end-btn button{background:#ff3b30!important}
.pulse{animation:pulse 1.5s infinite}
@keyframes pulse{0%{opacity:1}50%{opacity:0.5}100%{opacity:1}}
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

st.markdown(f"<div class='call-screen'><h3>Room: {st.session_state.room}</h3><p>👥 Live: {count} | Auto Call ON</p></div>",unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.session_state.my_listen=st.selectbox("I Listen:", ["Telugu","Hindi","Tamil","English"], index=["Telugu","Hindi","Tamil","English"].index(st.session_state.my_listen))

# 9 buttons
r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1"): st.info(f"Notes soon")
    st.markdown("<div class='label'>Notes</div>", unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2"): st.info(f"Code: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>", unsafe_allow_html=True)
with r1c3:
    if st.button("🔇" if not st.session_state.is_muted else "🎙️",key="b3"): st.session_state.is_muted=not st.session_state.is_muted; st.rerun()
    st.markdown("<div class='label'>Mute</div>", unsafe_allow_html=True)
r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("🔴" if st.session_state.is_live else "⚪",key="b4"): st.session_state.is_live=not st.session_state.is_live; st.rerun()
    st.markdown("<div class='label'>Translate ON</div>", unsafe_allow_html=True)
with r2c2:
    if st.button("📹",key="b5"): st.toast("Video soon")
    st.markdown("<div class='label'>Video</div>", unsafe_allow_html=True)
with r2c3:
    if st.button("⏸️",key="b6"): st.session_state.is_hold=not st.session_state.is_hold; st.rerun()
    st.markdown("<div class='label'>Hold</div>", unsafe_allow_html=True)
r3c1,r3c2,r3c3=st.columns(3)
with r3c1:
    if st.button("⌨️",key="b7"): pass
    st.markdown("<div class='label'>Keypad</div>", unsafe_allow_html=True)
with r3c2:
    st.markdown('<div class="end-btn">', unsafe_allow_html=True)
    if st.button("📞",key="b8"): st.session_state.room=None; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<div class='label'>End call</div>",unsafe_allow_html=True)
with r3c3:
    if st.button("🔊",key="b9"): pass
    st.markdown("<div class='label'>Speaker</div>",unsafe_allow_html=True)

st.divider()

# --- LEVEL 2.5: START = RECORD ---
BUFFER_RAW = f"room_data/{st.session_state.room}_{st.session_state.my_id}_live.raw"
META_FILE = f"room_data/{st.session_state.room}_{st.session_state.my_id}_meta.txt"

def audio_callback(frame: av.AudioFrame):
    if st.session_state.is_hold or st.session_state.is_muted or not st.session_state.is_live:
        return av.AudioFrame.from_ndarray(np.zeros((frame.samples, 2), dtype=np.int16), layout=frame.layout.name)
    try:
        arr = frame.to_ndarray()
        if not os.path.exists(META_FILE):
            open(META_FILE,"w").write(f"{frame.sample_rate}")
        with open(BUFFER_RAW,"ab") as f:
            f.write(arr.tobytes())
    except: pass
    return frame

st.markdown("### 🎤 START = Record ON | STOP = Auto Sent")
ctx = webrtc_streamer(key=f"voice-{st.session_state.room}", mode=WebRtcMode.SENDRECV, rtc_configuration=RTC_CONFIG, media_stream_constraints={"video":False,"audio":True}, audio_frame_callback=audio_callback, async_processing=True)

if ctx.state.playing:
    st.markdown("<div class='pulse' style='color:#ff3b30;text-align:center;font-weight:700'>🔴 LIVE Recording... Matladu!</div>", unsafe_allow_html=True)
    st.session_state.was_recording = True
else:
    if st.session_state.was_recording:
        st.session_state.was_recording = False
        if os.path.exists(BUFFER_RAW) and os.path.getsize(BUFFER_RAW) > 2000:
            with st.spinner("STOP - Sending..."):
                try:
                    sr = 48000
                    if os.path.exists(META_FILE):
                        try: sr = int(open(META_FILE,"r").read().split(",")[0])
                        except: pass
                    raw_data = open(BUFFER_RAW,"rb").read()
                    wav_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(raw_data)
                    os.remove(BUFFER_RAW)
                    if os.path.exists(META_FILE): os.remove(META_FILE)
                    with open(wav_path,"rb") as f:
                        try: stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
                        except:
                            f.seek(0)
                            stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
                        orig = getattr(stt_res, 'transcript', '') or str(stt_res)
                    if orig:
                        st.info(f"You said: {orig}")
                        bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
                        open(bfile,"w",encoding="utf-8").write(orig)
                        st.success("✅ Sent! Avathala vadiki auto ga vellipothundi - vaadu refresh nokka avasaram ledu")
                except Exception as e:
                    st.error(f"Error: {e}")
                    if os.path.exists(BUFFER_RAW): os.remove(BUFFER_RAW)
        else:
            st.warning("👇 START nokki matladu - STOP nokkithe auto Sent")

st.divider()

# --- LEVEL 2.5: AUTO INCOMING - NO REFRESH BUTTON ---
@st.fragment(run_every=2)
def auto_incoming():
    st.markdown(f"### 🔊 Live Incoming - {st.session_state.my_listen} lo (Auto 2 sec)")
    st.caption("Refresh avasaram ledu - auto ga vasthundi")
    broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
    broadcasts=[b for b in broadcasts if "_lang" not in b][:5]
    has_msg=False
    for bfile in broadcasts:
        try:
            if st.session_state.my_id in bfile: continue
            if time.time()-os.path.getmtime(bfile)>600: continue
            orig_text=open(bfile,"r",encoding="utf-8").read()
            sender=bfile.split("_")[-1].replace(".txt","")
            if not orig_text: continue
            has_msg=True
            tgt_code=lang_map[st.session_state.my_listen]
            cache_audio=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender}_{int(os.path.getmtime(bfile))}_{st.session_state.my_listen}.wav"
            cache_txt=cache_audio.replace(".wav",".txt")
            if not os.path.exists(cache_audio):
                with st.spinner(f"Translating to {st.session_state.my_listen}..."):
                    trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                    translated = getattr(trans_res, 'translated_text', orig_text)
                    open(cache_txt,"w",encoding="utf-8").write(f"{orig_text} -> {translated}")
                    try: tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anand", model="bulbul:v3")
                    except: tts_res = client.text_to_speech.convert(text=translated, language_code=tgt_code, speaker="anand", model="bulbul:v3")
                    ab64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                    if ab64:
                        try: data=base64.b64decode(ab64)
                        except: data=ab64.encode() if isinstance(ab64,str) else ab64
                        open(cache_audio,"wb").write(data)
            if os.path.exists(cache_audio):
                info=open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig_text
                st.markdown(f"**From {sender}:** {info}")
                st.audio(cache_audio, autoplay=True)
        except Exception as e:
            st.error(f"Translate Error: {e}")
    if not has_msg:
        st.info("No messages yet - Vere phone nundi matladagane ikkada auto ga vinipisthundi")

auto_incoming()
