import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, os, time, uuid, base64, glob
import numpy as np

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

# --- STATES (anni options) ---
for k,v in {"auth":False,"room":None,"is_muted":False,"is_live":False,"is_hold":False,"is_speaker":True,"is_video":False,"show_keypad":False,"show_notes":False,"my_id":str(uuid.uuid4())[:6],"notes_text":"","dial_number":"","my_listen":"Telugu"}.items():
    if k not in st.session_state: st.session_state[k]=v

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
            open(f"room_data/{st.session_state.room}.room","w").write("room")
            open(f"room_data/{st.session_state.room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n")
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join",use_container_width=True):
                rc=code.upper().strip().replace(" ","")
                os.makedirs("room_data",exist_ok=True)
                if not os.path.exists(f"room_data/{rc}.room") and not os.path.exists(f"room_data/{rc}_users.txt"):
                    st.error(f"❌ Room {rc} Not Found!")
                else:
                    st.session_state.room=rc; st.rerun()
    rooms=glob.glob("room_data/*.room")
    if rooms: st.info("Active: "+", ".join([os.path.basename(r).replace(".room","") for r in rooms][-5:]))
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.stButton>button{background:#2c2c2e!important;width:78px!important;height:78px!important;border-radius:50%!important;border:none!important;color:white!important;font-size:22px!important;margin:0 auto!important;display:block!important}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important;margin-top:6px!important}
.end-btn button{background:#ff3b30!important}
.notes-box{background:#1f2937;border-radius:12px;padding:15px;border:1px solid #333;margin-bottom:15px}
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
count=len(users)

status = "🔴 On Hold" if st.session_state.is_hold else "🔇 Muted" if st.session_state.is_muted else "🔴 LIVE" if st.session_state.is_live else "⚪ Paused"
st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{status} | Room: {st.session_state.room}</p></div>", unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: {count} | Room: {st.session_state.room}</div>",unsafe_allow_html=True)
if st.button("🔄 Refresh Live Count", use_container_width=True):
    st.rerun()

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
langs=["Telugu","Hindi","Tamil","English"]
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha / I Listen:", langs, index=langs.index(st.session_state.my_listen))

# --- NOTES ---
if st.session_state.show_notes:
    st.markdown("<div class='notes-box'>",unsafe_allow_html=True)
    st.markdown("### 📝 Call Notes")
    st.session_state.notes_text=st.text_area("",value=st.session_state.notes_text,height=100,key="notes_area")
    c1,c2=st.columns(2)
    if c1.button("💾 Save",use_container_width=True): open(f"room_data/{st.session_state.room}_notes.txt","w",encoding="utf-8").write(st.session_state.notes_text); st.success("Saved")
    if c2.button("❌ Close",use_container_width=True): st.session_state.show_notes=False; st.rerun()
    st.markdown("</div>",unsafe_allow_html=True)

# --- KEYPAD ---
if st.session_state.show_keypad:
    st.markdown(f"<h2 style='text-align:center'>{st.session_state.dial_number or ' '}</h2>",unsafe_allow_html=True)
    for row in [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]:
        a,b,c=st.columns(3)
        if a.button(row[0],key=f"k{row[0]}"): st.session_state.dial_number+=row[0]; st.rerun()
        if b.button(row[1],key=f"k{row[1]}"): st.session_state.dial_number+=row[1]; st.rerun()
        if c.button(row[2],key=f"k{row[2]}"): st.session_state.dial_number+=row[2]; st.rerun()
    if st.button("Close Keypad",use_container_width=True): st.session_state.show_keypad=False; st.rerun()

# --- 9 BUTTONS (anni options) ---
r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1"): st.session_state.show_notes=not st.session_state.show_notes; st.rerun()
    st.markdown("<div class='label'>Notes</div>", unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2"): st.info(f"Invite Code: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>", unsafe_allow_html=True)
with r1c3:
    if st.button("🔇" if not st.session_state.is_muted else "🎙️",key="b3"): st.session_state.is_muted=not st.session_state.is_muted; st.rerun()
    st.markdown("<div class='label'>Mute</div>", unsafe_allow_html=True)
r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("🔴" if st.session_state.is_live else "⚪",key="b4"): st.session_state.is_live=not st.session_state.is_live; st.rerun()
    st.markdown("<div class='label'>Translate ON</div>", unsafe_allow_html=True)
with r2c2:
    if st.button("📹",key="b5"): st.session_state.is_video=not st.session_state.is_video; st.toast("Video soon"); st.rerun()
    st.markdown("<div class='label'>Video call</div>", unsafe_allow_html=True)
with r2c3:
    if st.button("⏸️",key="b6"): st.session_state.is_hold=not st.session_state.is_hold; st.rerun()
    st.markdown("<div class='label'>Hold</div>", unsafe_allow_html=True)
r3c1,r3c2,r3c3=st.columns(3)
with r3c1:
    if st.button("⌨️",key="b7"): st.session_state.show_keypad=not st.session_state.show_keypad; st.rerun()
    st.markdown("<div class='label'>Keypad</div>", unsafe_allow_html=True)
with r3c2:
    st.markdown('<div class="end-btn">', unsafe_allow_html=True)
    if st.button("📞",key="b8"):
        if st.session_state.my_id in users: del users[st.session_state.my_id]
        with open(cf,"w") as f:
            for uid,t in users.items(): f.write(f"{uid}|{t}\n")
        st.session_state.room=None; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<div class='label'>End call</div>",unsafe_allow_html=True)
with r3c3:
    if st.button("🔊",key="b9"): st.session_state.is_speaker=not st.session_state.is_speaker; st.rerun()
    st.markdown("<div class='label'>Speaker</div>",unsafe_allow_html=True)

st.divider()

# --- START MIC (STABLE - auto rerun ledu) ---
def audio_callback(frame: av.AudioFrame):
    if st.session_state.is_hold or st.session_state.is_muted or not st.session_state.is_live:
        return av.AudioFrame.from_ndarray(np.zeros((frame.samples, 2), dtype=np.int16), layout=frame.layout.name)
    return frame

ctx = webrtc_streamer(
    key=f"voice-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    audio_frame_callback=audio_callback,
    async_processing=True,
)
if ctx.state.playing: st.success("🎙️ Mic ON - stable ga untundi")
else: st.warning("👇 START nokki mic allow chey - ippudu 1-2 sec lo off avvadu")

st.divider()
st.markdown("### 🎤 Matladu - Auto-detect & Translate")
audio = st.audio_input("Mic nokki matladu", key="mic_input")

if audio and st.session_state.is_live:
    in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
    with open(in_path,"wb") as f: f.write(audio.getbuffer())
    with st.spinner("Sending..."):
        try:
            try:
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
                    orig = getattr(stt_res, 'transcript', '') or str(stt_res)
            except:
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
                    orig = getattr(stt_res, 'transcript', '') or str(stt_res)
            if orig:
                st.info(f"You said: {orig}")
                bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
                open(bfile,"w",encoding="utf-8").write(orig)
                open(bfile.replace(".txt","_lang.txt"),"w").write("auto")
                st.success("✅ Sent!")
        except Exception as e: st.error(f"STT Error: {e}")
elif audio and not st.session_state.is_live:
    st.warning("Translate ON (🔴) chey")

st.divider()
st.markdown(f"### 🔊 Incoming - {st.session_state.my_listen} lo")
broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
broadcasts=[b for b in broadcasts if "_lang" not in b][:5]
for bfile in broadcasts:
    try:
        if st.session_state.my_id in bfile: continue
        if time.time()-os.path.getmtime(bfile)>300: continue
        orig_text=open(bfile,"r",encoding="utf-8").read()
        sender=bfile.split("_")[-1].replace(".txt","")
        if not orig_text: continue
        tgt_code=lang_map[st.session_state.my_listen]
        cache_audio=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender}_{int(os.path.getmtime(bfile))}_{st.session_state.my_listen}.wav"
        cache_txt=cache_audio.replace(".wav",".txt")
        if not os.path.exists(cache_audio):
            with st.spinner(f"Translating..."):
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
            st.audio(cache_audio)
    except Exception as e: st.error(f"Translate Error: {e}")

if st.button("🔄 Refresh Incoming",use_container_width=True, type="primary"):
    st.rerun()

# NOTE: time.sleep + auto rerun teesesanu - anduke mic stable
