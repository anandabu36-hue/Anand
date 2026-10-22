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

for k,v in {"auth":False,"room":None,"is_muted":False,"is_live":False,"is_hold":False,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu"}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator</h2>",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create",use_container_width=True,type="primary"):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            os.makedirs("room_data",exist_ok=True)
            open(f"room_data/{st.session_state.room}.room","w").write("room")
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
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important}
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

st.markdown(f"<div class='call-screen'><h3>Room: {st.session_state.room}</h3><p>👥 Live: {count} | {'🔴 LIVE' if st.session_state.is_live else '⚪ Paused'}</p></div>",unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: {count} | Auto-refresh ON</div>",unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
langs=["Telugu","Hindi","Tamil","English"]
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha (I Listen):", langs, index=langs.index(st.session_state.my_listen))
st.caption(f"Nuvvu em matladina auto-detect, avathala vadiki {st.session_state.my_listen} lo veltundi")

if st.button("🔴 LIVE ON / OFF",use_container_width=True,type="primary"):
    st.session_state.is_live=not st.session_state.is_live; st.rerun()
if st.button("📞 End Call",use_container_width=True):
    if st.session_state.my_id in users: del users[st.session_state.my_id]
    with open(cf,"w") as f:
        for uid,t in users.items(): f.write(f"{uid}|{t}\n")
    st.session_state.room=None; st.rerun()

st.divider()
st.markdown("### 🎤 START nokki matladu - Auto Record & Translate")

# --- WEbrtc + Auto Recording ---
def audio_callback(frame: av.AudioFrame):
    if st.session_state.is_hold or st.session_state.is_muted or not st.session_state.is_live:
        return frame
    return frame

ctx = webrtc_streamer(
    key=f"voice-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    audio_frame_callback=audio_callback,
    async_processing=True,
)

# --- REAL WORKING: Push to Talk but Auto ---
# WebRTC voice veladhu kabatti, manam audio_input ni auto ga vadutham
st.markdown("**Matladina tarvata auto ga translate ayi velthundi**")
audio = st.audio_input("Mic nokki matladu - 5 sec matladi aapu", key=f"mic_{int(now)}")

if audio and st.session_state.is_live:
    in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
    with open(in_path,"wb") as f: f.write(audio.getbuffer())
    with st.spinner("Auto-detecting language & sending..."):
        try:
            # === AUTO LANGUAGE DETECT (I SPEAK REMOVED) ===
            # Try without language_code for auto-detect
            try:
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
                    orig = getattr(stt_res, 'transcript', '') or str(stt_res)
            except:
                # fallback telugu
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
                    orig = getattr(stt_res, 'transcript', '') or str(stt_res)
            
            if orig:
                st.info(f"You said: {orig}")
                # Detect source language crudely or keep auto for translate
                bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
                open(bfile,"w",encoding="utf-8").write(orig)
                # Save auto lang marker
                open(bfile.replace(".txt","_lang.txt"),"w").write("auto")
                st.success("✅ Sent! Avathala vadiki auto-translate ayi veltundi")
        except Exception as e:
            st.error(f"STT Error: {e}")

st.divider()
st.markdown(f"### 🔊 Incoming - Neeku {st.session_state.my_listen} lo (Auto)")

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
            with st.spinner(f"Translating to {st.session_state.my_listen}..."):
                trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                translated = getattr(trans_res, 'translated_text', orig_text)
                open(cache_txt,"w",encoding="utf-8").write(f"{orig_text} -> {translated}")
                try:
                    tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anand", model="bulbul:v3")
                except TypeError:
                    tts_res = client.text_to_speech.convert(text=translated, language_code=tgt_code, speaker="anand", model="bulbul:v3")
                audio_b64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                if audio_b64:
                    try: data=base64.b64decode(audio_b64)
                    except: data=audio_b64.encode() if isinstance(audio_b64,str) else audio_b64
                    open(cache_audio,"wb").write(data)
        if os.path.exists(cache_audio):
            info=open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig_text
            st.markdown(f"**From {sender}:** {info}")
            st.audio(cache_audio, autoplay=True)
    except Exception as e:
        st.error(f"Translate Error: {e}")

# Auto refresh for live count + incoming
time.sleep(3)
st.rerun()
