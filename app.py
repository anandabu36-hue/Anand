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

# --- ALL STATES ---
for k,v in {"auth":False,"room":None,"is_muted":False,"is_live":False,"is_hold":False,"is_speaker":False,"is_video":False,"show_keypad":False,"show_notes":False,"my_id":str(uuid.uuid4())[:6],"notes_text":"","dial_number":"","my_speak":"Telugu","my_listen":"Hindi"}.items():
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
            code=st.text_input("Room Code (ex: ANAND-DOCC)")
            if st.form_submit_button("Join",use_container_width=True):
                rc=code.upper().strip().replace(" ","")
                if not rc: st.error("Code enter chey")
                else:
                    os.makedirs("room_data",exist_ok=True)
                    open(f"room_data/{rc}.room","w").write("room")
                    if not os.path.exists(f"room_data/{rc}_users.txt"):
                        open(f"room_data/{rc}_users.txt","w").write("")
                    st.session_state.room=rc; st.rerun()
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.stButton>button{background:#2c2c2e!important;width:78px!important;height:78px!important;border-radius:50%!important;border:none!important;color:white!important;font-size:22px!important;margin:0 auto!important;display:block!important}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important;margin-top:6px!important}
.end-btn button{background:#ff3b30!important}
</style>
""", unsafe_allow_html=True)

# --- LIVE COUNT FIX ---
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
st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{status} | Speaker: {'ON' if st.session_state.is_speaker else 'OFF'}<br>Room: {st.session_state.room}</p></div>", unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: {count} | Room: {st.session_state.room}</div>",unsafe_allow_html=True)

if st.session_state.show_notes:
    st.markdown("### 📝 Notes")
    st.session_state.notes_text = st.text_area("Call Notes:", value=st.session_state.notes_text, height=100)
    c1,c2=st.columns(2)
    if c1.button("💾 Save"): open(f"room_data/{st.session_state.room}_notes.txt","w",encoding="utf-8").write(st.session_state.notes_text); st.success("Saved")
    if c2.button("Close Notes"): st.session_state.show_notes=False; st.rerun()

if st.session_state.show_keypad:
    st.markdown(f"### ⌨️ Dial: {st.session_state.dial_number}")
    k1,k2,k3=st.columns(3)
    with k1: 
        if st.button("1",key="k1"): st.session_state.dial_number+="1"; st.rerun()
        if st.button("4",key="k4"): st.session_state.dial_number+="4"; st.rerun()
        if st.button("7",key="k7"): st.session_state.dial_number+="7"; st.rerun()
        if st.button("*",key="ks"): st.session_state.dial_number+="*"; st.rerun()
    with k2:
        if st.button("2",key="k2"): st.session_state.dial_number+="2"; st.rerun()
        if st.button("5",key="k5"): st.session_state.dial_number+="5"; st.rerun()
        if st.button("8",key="k8"): st.session_state.dial_number+="8"; st.rerun()
        if st.button("0",key="k0"): st.session_state.dial_number+="0"; st.rerun()
    with k3:
        if st.button("3",key="k3"): st.session_state.dial_number+="3"; st.rerun()
        if st.button("6",key="k6"): st.session_state.dial_number+="6"; st.rerun()
        if st.button("9",key="k9"): st.session_state.dial_number+="9"; st.rerun()
        if st.button("#",key="kh"): st.session_state.dial_number+="#"; st.rerun()
    if st.button("Clear"): st.session_state.dial_number=""; st.rerun()
    if st.button("Close Keypad"): st.session_state.show_keypad=False; st.rerun()

# === FIX FOR YOUR 1ST POINT - MY SPEAK + MY LISTEN ===
lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
langs=["Telugu","Hindi","Tamil","English"]
c1,c2=st.columns(2)
with c1:
    st.session_state.my_speak=st.selectbox("I Speak:", langs, index=langs.index(st.session_state.my_speak))
with c2:
    st.session_state.my_listen=st.selectbox("I Want to Listen In:", langs, index=langs.index(st.session_state.my_listen))
st.caption(f"Avathala vadu em matladina neeku {st.session_state.my_listen} lo vinipistundi")

# --- 9 BUTTONS ---
r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1"): st.session_state.show_notes=not st.session_state.show_notes; st.rerun()
    st.markdown("<div class='label'>Notes</div>", unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2"): st.toast(f"Invite Code: {st.session_state.room}"); st.info(f"Share Room Code {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>", unsafe_allow_html=True)
with r1c3:
    if st.button("🔇" if not st.session_state.is_muted else "🎙️",key="b3"): st.session_state.is_muted=not st.session_state.is_muted; st.rerun()
    st.markdown("<div class='label'>Mute</div>", unsafe_allow_html=True)

r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("🔴" if st.session_state.is_live else "⚪",key="b4"): st.session_state.is_live=not st.session_state.is_live; st.rerun()
    st.markdown("<div class='label'>Translate ON</div>", unsafe_allow_html=True)
with r2c2:
    if st.button("📹",key="b5"): st.session_state.is_video=not st.session_state.is_video; st.rerun()
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

# --- VOICE LIVE (WebRTC) ---
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
if ctx.state.playing: st.success("🎙️ Mic ON")
else: st.warning("👇 START nokki mic allow chey")

st.divider()

# === NEW: PUSH TO TALK WITH PER-RECEIVER TRANSLATION ===
st.markdown("### 🎤 Push to Talk - Translate chesi pampisthundi")
audio = st.audio_input(f"Mic nokki {st.session_state.my_speak} lo matladu")

if audio:
    in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
    with open(in_path,"wb") as f: f.write(audio.getbuffer())
    if st.session_state.is_live and not st.session_state.is_hold and not st.session_state.is_muted:
        with st.spinner(f"{st.session_state.my_speak} processing..."):
            try:
                speak_code=lang_map[st.session_state.my_speak]
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code=speak_code)
                    orig = getattr(stt_res, 'transcript', '') or str(stt_res)
                st.info(f"You said ({st.session_state.my_speak}): {orig}")
                # Save for ALL other users - they will translate to THEIR language on refresh
                bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
                open(bfile,"w",encoding="utf-8").write(orig)
                open(bfile.replace(".txt","_lang.txt"),"w").write(speak_code)
                st.success("Sent! Avathala vadu refresh chesthe vadiki vadi language lo vinipistundi")
            except Exception as e:
                st.error(f"STT Error: {e}")
    else:
        st.warning("Translate ON chey, Hold/Mute off chey")

st.divider()
st.markdown(f"### 🔊 Incoming - Neeku {st.session_state.my_listen} lo vinipistundi")

broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
broadcasts=[b for b in broadcasts if "_lang" not in b][:5]

if not broadcasts:
    st.caption("Inka voice ledu - rendu phones lo SAME code join avvu")
else:
    for bfile in broadcasts:
        try:
            if st.session_state.my_id in bfile: continue
            if time.time()-os.path.getmtime(bfile)>300: continue
            orig_text=open(bfile,"r",encoding="utf-8").read()
            sender=bfile.split("_")[-1].replace(".txt","")
            lang_file=bfile.replace(".txt","_lang.txt")
            src_code=open(lang_file,"r").read().strip() if os.path.exists(lang_file) else "te-IN"
            if not orig_text: continue
            
            tgt_code=lang_map[st.session_state.my_listen]
            # Skip if same language
            if src_code==tgt_code:
                translated=orig_text
            else:
                cache_txt=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender}_{int(os.path.getmtime(bfile))}_{st.session_state.my_listen}.txt"
                cache_audio=cache_txt.replace(".txt",".wav")
                if not os.path.exists(cache_audio):
                    # FIX: explicit source language - no auto
                    trans_res = client.text.translate(input=orig_text, source_language_code=src_code, target_language_code=tgt_code)
                    translated = getattr(trans_res, 'translated_text', orig_text)
                    open(cache_txt,"w",encoding="utf-8").write(f"{orig_text} -> {translated}")
                    # FIX: TTS param
                    try:
                        tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anushka", model="bulbul:v2")
                    except TypeError:
                        tts_res = client.text_to_speech.convert(text=translated, language_code=tgt_code, speaker="anushka", model="bulbul:v2")
                    audio_b64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                    if audio_b64:
                        try: data=base64.b64decode(audio_b64)
                        except: data=audio_b64.encode() if isinstance(audio_b64,str) else audio_b64
                        open(cache_audio,"wb").write(data)
                else:
                    translated=open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig_text
            
            st.markdown(f"**From {sender} ({src_code} -> {tgt_code}):** {orig_text} -> {translated if 'translated' in locals() else orig_text}")
            if os.path.exists(cache_audio if 'cache_audio' in locals() else ""):
                st.audio(cache_audio)
            elif src_code==tgt_code:
                st.caption("Same language - no translation needed")
        except Exception as e:
            st.error(f"Translate Error: {e}")

if st.button("🔄 Refresh to get new translated voice",use_container_width=True, type="primary"):
    st.rerun()
