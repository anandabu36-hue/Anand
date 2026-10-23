import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os, time, uuid, base64, glob

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu"}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data",exist_ok=True)

if not st.session_state.room:
    st.markdown("<div style='background:linear-gradient(90deg,#4facfe,#1a237e);border-radius:20px;padding:20px;color:white;text-align:center'><h2>📞 Anand Translator</h2><p>Stable - Guaranteed Working</p></div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create",use_container_width=True,type="primary"):
            new_room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=new_room
            open(f"room_data/{new_room}.room","w").write("room")
            open(f"room_data/{new_room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n")
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join",use_container_width=True):
                rc=code.upper().strip().replace(" ","")
                if os.path.exists(f"room_data/{rc}.room") or os.path.exists(f"room_data/{rc}_users.txt"):
                    st.session_state.room=rc; st.rerun()
                else:
                    st.error(f"❌ Room {rc} Not Found!")
    rooms=glob.glob("room_data/*.room")
    if rooms: st.info("Active: "+", ".join([os.path.basename(r).replace(".room","") for r in rooms][-5:]))
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important;margin-top:6px!important}
.end-btn button{background:#ff3b30!important}
</style>
""", unsafe_allow_html=True)

# Live count - 60 sec
cf=f"room_data/{st.session_state.room}_users.txt"
now=time.time()
users={}
if os.path.exists(cf):
    with open(cf,"r") as f:
        for l in f:
            if "|" in l:
                try:
                    uid,t=l.strip().split("|")
                    if now-float(t)<60: users[uid]=float(t)
                except: pass
users[st.session_state.my_id]=now
with open(cf,"w") as f:
    for uid,t in users.items(): f.write(f"{uid}|{t}\n")

st.markdown(f"<div class='call-screen'><h3>Room: {st.session_state.room}</h3><p>👥 Live: {len(users)} | My ID: {st.session_state.my_id}</p></div>",unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: {len(users)} | Room: {st.session_state.room}</div>",unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha / I Listen:", ["Telugu","Hindi","Tamil","English"], index=["Telugu","Hindi","Tamil","English"].index(st.session_state.my_listen))

# 9 buttons same
r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1"): st.info("Notes")
    st.markdown("<div class='label'>Notes</div>", unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2"): st.info(f"Invite: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>", unsafe_allow_html=True)
with r1c3:
    if st.button("🔇",key="b3"): st.toast("Mute")
    st.markdown("<div class='label'>Mute</div>", unsafe_allow_html=True)
r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("🔴",key="b4"): st.toast("Translate ON")
    st.markdown("<div class='label'>Translate ON</div>", unsafe_allow_html=True)
with r2c2:
    if st.button("📹",key="b5"): st.toast("Video soon")
    st.markdown("<div class='label'>Video</div>", unsafe_allow_html=True)
with r2c3:
    if st.button("⏸️",key="b6"): st.toast("Hold")
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

# --- STABLE MIC INDICATOR (webrtc only for show) ---
st.markdown("### Step 1: Mic Connect (Stable)")
ctx = webrtc_streamer(
    key=f"voice-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    async_processing=True,
)
if ctx.state.playing: st.success("🎙️ Mic Connected - Ippudu kindha matladu")
else: st.warning("👇 START nokki mic allow chey - tarvata kindha mic lo matladu")

st.divider()
st.markdown("### Step 2: Matladu - Ikkada START/STOP untundi")

audio = st.audio_input("Mic nokki matladu, aapagane auto Sent avuthundi", key="mic_input")

if audio:
    in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
    with open(in_path,"wb") as f: f.write(audio.getbuffer())
    with st.spinner("Sending to room..."):
        try:
            with open(in_path,"rb") as f:
                try:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
                except:
                    f.seek(0)
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
                orig = getattr(stt_res, 'transcript', '') or str(stt_res)
            if orig:
                st.info(f"You said: {orig}")
                bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
                open(bfile,"w",encoding="utf-8").write(orig)
                st.success(f"✅ Sent to {st.session_state.room}! Vere phone lo 2 sec lo auto ga vinipisthundi")
        except Exception as e:
            st.error(f"STT Error: {e}")

st.divider()

@st.fragment(run_every=2)
def auto_incoming():
    st.markdown(f"### 🔊 Live Incoming - {st.session_state.my_listen} lo (Auto)")
    st.caption("Refresh avasaram ledu - auto ga 2 sec ki vasthundi")
    broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
    broadcasts=[b for b in broadcasts if "_lang" not in b][:5]
    found=False
    for bfile in broadcasts:
        try:
            if st.session_state.my_id in bfile: continue
            if time.time()-os.path.getmtime(bfile)>600: continue
            orig_text=open(bfile,"r",encoding="utf-8").read()
            sender=bfile.split("_")[-1].replace(".txt","")
            if not orig_text: continue
            found=True
            tgt_code=lang_map[st.session_state.my_listen]
            cache_audio=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender}_{int(os.path.getmtime(bfile))}_{st.session_state.my_listen}.wav"
            cache_txt=cache_audio.replace(".wav",".txt")
            if not os.path.exists(cache_audio):
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
    if not found:
        st.info(f"No messages yet in {st.session_state.room}")

auto_incoming()
