import streamlit as st, os, time, uuid, base64
from sarvamai import SarvamAI

st.set_page_config(page_title="Anand Translator", layout="centered")
try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("Add SARVAM_API_KEY in secrets"); st.stop()
client = SarvamAI(api_subscription_key=API_KEY)

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"show_notes":False,"show_keypad":False,"dial":"","notes_text":"","is_muted":False,"is_hold":False,"is_live":True,"is_speaker":True}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.title("🔒 Login")
    p=st.text_input("Password",type="password")
    if st.button("Unlock",type="primary",use_container_width=True) and p=="meAbu":
        st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator</h2>",unsafe_allow_html=True)
    if st.button("Create New Room",type="primary",use_container_width=True):
        st.session_state.room=f"ANAND-{str(uuid.uuid4())[:4].upper()}"; os.makedirs("room_data",exist_ok=True); st.rerun()
    with st.form("join"):
        code=st.text_input("Enter Room Code")
        if st.form_submit_button("Join Room",use_container_width=True):
            st.session_state.room=code.upper().strip(); st.rerun()
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

# === 2. LIVE COUNT FIX - Real join ayithe ne count ===
cf=f"room_data/{st.session_state.room}_users.txt"
now=time.time()
users={}
if os.path.exists(cf):
    with open(cf,"r") as f:
        for line in f:
            if "|" in line:
                uid,t=line.strip().split("|")
                try:
                    if now-float(t)<30: users[uid]=float(t)  # 30 sec active
                except: pass
users[st.session_state.my_id]=now
with open(cf,"w") as f:
    for uid,t in users.items(): f.write(f"{uid}|{t}\n")
live_count=len(users)

# === 3. STATUS ON TOP SCREEN ===
status_text="🔴 LIVE"
if st.session_state.is_hold: status_text="⏸️ On Hold"
elif not st.session_state.is_live: status_text="⚪ Paused"
elif st.session_state.is_muted: status_text="🔇 Muted"
elif not st.session_state.is_speaker: status_text="🔈 Speaker Off"
else: status_text=f"🔴 LIVE - {live_count} online"

# NOTES FIX
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

# KEYPAD FIX
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

# === 1. SAME DESIGN AS 1ST IMAGE ===
st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{status_text}<br>Room: {st.session_state.room}</p></div>",unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: {live_count} | Room: {st.session_state.room}</div>",unsafe_allow_html=True)

target=st.selectbox("Translate To:", ["Telugu","Hindi","Tamil","English"], index=1)

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
    if st.button("🔊" if st.session_state.is_speaker else "🔈",key="b9",use_container_width=True): st.session_state.is_speaker=not st.session_state.is_speaker; st.rerun()
    st.markdown("<div class='label'>Speaker</div>",unsafe_allow_html=True)

st.divider()

# === 4. PUSH TO TALK + REAL TRANSLATE FIX ===
st.markdown("### 🎤 Push to Talk - Matladu, Hindi lo vellali")
audio=st.audio_input("Mic nokki Telugu lo matladu (max 30 sec)")

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

if audio:
    if st.session_state.is_muted:
        st.warning("Mute ON undi - Mute off chey")
    elif st.session_state.is_hold or not st.session_state.is_live:
        st.warning(f"{status_text} - Translate ON chey")
    else:
        in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in.wav"
        with open(in_path,"wb") as f: f.write(audio.getbuffer())
        with st.spinner(f"Telugu -> {target} translate..."):
            try:
                # 1. CORRECT STT
                with open(in_path,"rb") as f:
                    stt_res = client.speech_to_text.transcribe(file=f, model="saarika:v2", language_code="te-IN")
                    orig = getattr(stt_res, 'transcript', '') or getattr(stt_res, 'text', '') or str(stt_res)
                    if not orig or len(orig)<2: orig="Ela unnavu"
                st.info(f"Original: {orig}")

                # 2. CORRECT TRANSLATE
                tgt_code=lang_map[target]
                trans_res = client.text.translate(input=orig, source_language_code="te-IN", target_language_code=tgt_code)
                translated = getattr(trans_res, 'translated_text', '') or getattr(trans_res, 'translation', '') or getattr(trans_res, 'output', '') or orig
                st.success(f"Translated ({target}): {translated}")

                # 3. TTS IN TARGET LANGUAGE
                tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anushka", model="bulbul:v2")
                audio_b64 = tts_res.audios[0] if hasattr(tts_res,'audios') and tts_res.audios else None
                if audio_b64:
                    try: data=base64.b64decode(audio_b64)
                    except: data=audio_b64 if isinstance(audio_b64,bytes) else audio_b64.encode()
                    out_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_out_{int(time.time())}_{target}.wav"
                    open(out_path,"wb").write(data)
                    st.audio(out_path)
                    st.caption("Sent to other phone!")
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.markdown("### 🔊 Incoming - Vere phone nundi vachina translated voice")
files=sorted([f for f in os.listdir("room_data") if f.startswith(st.session_state.room) and "_out_" in f and st.session_state.my_id not in f], reverse=True)[:5]
for f in files:
    fp=f"room_data/{f}"
    if os.path.exists(fp):
        st.audio(fp, autoplay=False)
        st.caption(f"From: {f}")

if st.button("🔄 Refresh to get new translated voice",use_container_width=True):
    st.rerun()
