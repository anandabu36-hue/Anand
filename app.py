import streamlit as st, os, time, uuid, base64, glob
from sarvamai import SarvamAI

st.set_page_config(page_title="Anand Translator", layout="centered")
try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("Add SARVAM_API_KEY"); st.stop()
client = SarvamAI(api_subscription_key=API_KEY)

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"show_notes":False,"show_keypad":False,"dial":"","notes_text":"","is_muted":False,"is_hold":False,"is_live":True,"is_speaker":True,"my_listen_lang":"Telugu"}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.title("🔒 Login")
    p=st.text_input("Password",type="password")
    if st.button("Unlock",type="primary",use_container_width=True) and p=="meAbu":
        st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator</h2>",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("Create New Room",type="primary",use_container_width=True):
            st.session_state.room=f"ANAND-{str(uuid.uuid4())[:4].upper()}"
            os.makedirs("room_data",exist_ok=True)
            # Create empty room marker
            open(f"room_data/{st.session_state.room}.room","w").write("room")
            st.rerun()
    with c2:
        if st.button("Active Rooms",use_container_width=True):
            rooms=glob.glob("room_data/*.room")
            if rooms: st.info("Active: "+", ".join([os.path.basename(r).replace('.room','') for r in rooms][-5:]))
            else: st.info("No active rooms")

    with st.form("join"):
        code=st.text_input("Enter Room Code (ex: ANAND-057B)", placeholder="ANAND-XXXX")
        j=st.form_submit_button("Join Room",use_container_width=True, type="primary")
        if j:
            rc=code.upper().strip().replace(" ","")
            if not rc:
                st.error("Code enter chey")
            else:
                # FIX 1: Same code tho join avvali - check and allow
                # If .room file ledu kuda allow, but create marker
                os.makedirs("room_data",exist_ok=True)
                if not os.path.exists(f"room_data/{rc}.room"):
                    # If user typed existing ANAND code but marker ledu, still allow and create
                    open(f"room_data/{rc}.room","w").write("room")
                st.session_state.room=rc
                st.success(f"Joined {rc}")
                time.sleep(0.5)
                st.rerun()
    st.stop()

st.markdown("""
<style>
.block-container{max-width:480px!important}.stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.notes-box{background:#1f2937;border-radius:12px;padding:15px;border:1px solid #333;margin-bottom:15px}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important}
.end-btn button{background:#ff3b30!important}
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
live_count=len(users)

status_text="🔴 LIVE"
if st.session_state.is_hold: status_text="⏸️ On Hold"
elif not st.session_state.is_live: status_text="⚪ Paused"
elif st.session_state.is_muted: status_text="🔇 Muted"
else: status_text=f"🔴 LIVE - {live_count} online"

if st.session_state.show_notes:
    st.markdown("<div class='notes-box'>",unsafe_allow_html=True)
    st.markdown("### 📝 Call Notes")
    st.session_state.notes_text=st.text_area("",value=st.session_state.notes_text,height=150,key="notes_area")
    c1,c2=st.columns(2)
    if c1.button("💾 Save",type="primary",use_container_width=True):
        open(f"room_data/{st.session_state.room}_notes.txt","w",encoding="utf-8").write(st.session_state.notes_text); st.success("Saved")
    if c2.button("❌ Close",use_container_width=True):
        st.session_state.show_notes=False; st.rerun()
    st.markdown("</div>",unsafe_allow_html=True)

if st.session_state.show_keypad:
    st.markdown(f"<div class='call-screen'><h3>{st.session_state.dial or ' '}</h3><p>Room: {st.session_state.room}</p></div>",unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align:center;color:white;font-size:48px'>{st.session_state.dial}</h1>",unsafe_allow_html=True)
    for row in [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]:
        a,b,c=st.columns(3)
        if a.button(row[0],key=f"kp{row[0]}",use_container_width=True): st.session_state.dial+=row[0]; st.rerun()
        if b.button(row[1],key=f"kp{row[1]}",use_container_width=True): st.session_state.dial+=row[1]; st.rerun()
        if c.button(row[2],key=f"kp{row[2]}",use_container_width=True): st.session_state.dial+=row[2]; st.rerun()
    if st.button("⌨️ Hide Keypad",use_container_width=True):
        st.session_state.show_keypad=False; st.rerun()
    st.divider()

st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{status_text}<br>Room: {st.session_state.room}</p></div>",unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: {live_count} | Room: {st.session_state.room}</div>",unsafe_allow_html=True)

# FIX 2: My Listening Language - avathala vadu em matladina neeku ee bhashalo
st.session_state.my_listen_lang = st.selectbox("Nenu Vinalanukune Bhasha / My Listening Language:", ["Telugu","Hindi","Tamil","English"], index=["Telugu","Hindi","Tamil","English"].index(st.session_state.my_listen_lang))
st.caption(f"Avathala vallu em matladina neeku {st.session_state.my_listen_lang} lo vinipistundi")

r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1",use_container_width=True): st.session_state.show_notes=not st.session_state.show_notes; st.rerun()
    st.markdown("<div class='label'>Notes</div>",unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2",use_container_width=True): st.info(f"Code: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>",unsafe_allow_html=True)
with r1c3:
    if st.button("🔇" if not st.session_state.is_muted else "🎙️",key="b3",use_container_width=True): st.session_state.is_muted=not st.session_state.is_muted; st.rerun()
    st.markdown("<div class='label'>Mute</div>",unsafe_allow_html=True)
r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("🔴" if st.session_state.is_live else "⚪",key="b4",use_container_width=True): st.session_state.is_live=not st.session_state.is_live; st.rerun()
    st.markdown("<div class='label'>Translate ON</div>",unsafe_allow_html=True)
with r2c2:
    if st.button("📹",key="b5",use_container_width=True): st.toast("Video soon")
    st.markdown("<div class='label'>Video call</div>",unsafe_allow_html=True)
with r2c3:
    if st.button("⏸️",key="b6",use_container_width=True): st.session_state.is_hold=not st.session_state.is_hold; st.rerun()
    st.markdown("<div class='label'>Hold</div>",unsafe_allow_html=True)
r3c1,r3c2,r3c3=st.columns(3)
with r3c1:
    if st.button("⌨️",key="b7",use_container_width=True): st.session_state.show_keypad=not st.session_state.show_keypad; st.rerun()
    st.markdown("<div class='label'>Keypad</div>",unsafe_allow_html=True)
with r3c2:
    st.markdown('<div class="end-btn">',unsafe_allow_html=True)
    if st.button("📞",key="b8",use_container_width=True): 
        if st.session_state.my_id in users: del users[st.session_state.my_id]
        with open(cf,"w") as f:
            for uid,t in users.items(): f.write(f"{uid}|{t}\n")
        st.session_state.room=None; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<div class='label'>End call</div>",unsafe_allow_html=True)
with r3c3:
    if st.button("🔊",key="b9",use_container_width=True): st.session_state.is_speaker=not st.session_state.is_speaker; st.rerun()
    st.markdown("<div class='label'>Speaker</div>",unsafe_allow_html=True)

st.divider()
st.markdown("### 🎤 Push to Talk")
audio=st.audio_input("Mic nokki matladu - avathala vallaki veltundi")

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

if audio:
    if st.session_state.is_muted: st.warning("Mute ON")
    elif st.session_state.is_hold or not st.session_state.is_live: st.warning(status_text)
    else:
        in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
        with open(in_path,"wb") as f: f.write(audio.getbuffer())
        with st.spinner("Processing..."):
            try:
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="te-IN")
                    orig = getattr(stt_res, 'transcript', '') or str(stt_res)
                st.info(f"You said: {orig}")
                # Save for OTHER user - common file
                open(f"room_data/{st.session_state.room}_{st.session_state.my_id}_last.txt","w",encoding="utf-8").write(orig)
                # Also save in room broadcast file
                open(f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt","w",encoding="utf-8").write(orig)
            except Exception as e:
                st.error(f"STT Error: {e}")

st.divider()
st.markdown(f"### 🔊 Incoming - Neeku {st.session_state.my_listen_lang} lo")
# FIX 2: Avathala vadu matladindi naku na language lo auto translate
broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)[:5]
if not broadcasts:
    st.caption("Inka voice raledu - rendu phones lo SAME room code enter chey")
for bfile in broadcasts:
    try:
        if st.session_state.my_id in bfile: continue
        mtime=os.path.getmtime(bfile)
        if time.time()-mtime>300: continue
        orig_text=open(bfile,"r",encoding="utf-8").read()
        sender=bfile.split("_")[-1].replace(".txt","")
        if not orig_text: continue
        
        tgt_code=lang_map[st.session_state.my_listen_lang]
        cache_audio=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender}_{int(mtime)}_{st.session_state.my_listen_lang}.wav"
        
        if not os.path.exists(cache_audio):
            with st.spinner(f"Translating to {st.session_state.my_listen_lang}..."):
                trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                translated = getattr(trans_res, 'translated_text', orig_text)
                tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anushka", model="bulbul:v2")
                audio_b64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                if audio_b64:
                    try: data=base64.b64decode(audio_b64)
                    except: data=audio_b64.encode() if isinstance(audio_b64,str) else audio_b64
                    open(cache_audio,"wb").write(data)
                    open(cache_audio.replace(".wav",".txt"),"w",encoding="utf-8").write(f"{orig_text} -> {translated}")
        
        if os.path.exists(cache_audio):
            txt_info=""
            if os.path.exists(cache_audio.replace(".wav",".txt")):
                txt_info=open(cache_audio.replace(".wav",".txt"),"r",encoding="utf-8").read()
            st.markdown(f"**From {sender}:** {txt_info}")
            st.audio(cache_audio, autoplay=True)
    except Exception as e:
        st.error(f"Translate Error: {e}")

if st.button("🔄 Refresh to get new translated voice",use_container_width=True, type="primary"):
    st.rerun()
