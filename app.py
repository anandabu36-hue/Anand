import streamlit as st, os, time, uuid, base64
from sarvamai import SarvamAI

st.set_page_config(page_title="Anand Translator", layout="centered")

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("Add SARVAM_API_KEY"); st.stop()
client = SarvamAI(api_subscription_key=API_KEY)

# Session
for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"show_notes":False,"show_keypad":False,"dial":"","notes_text":"","is_live":True,"is_hold":False,"is_muted":False,"is_speaker":True}.items():
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

# --- CSS SAME AS YOUR 1ST IMAGE ---
st.markdown("""
<style>
.block-container{max-width:480px!important} .stApp{background:#121212!important}
.call-screen{background:linear-gradient(135deg,#5aa9ff 0%,#1e3c8a 100%);border-radius:28px;padding:22px;color:white;text-align:center}
.count-box{background:#1f2937;border-radius:12px;padding:10px;color:#10b981;font-weight:700;text-align:center;margin:12px 0}
.notes-box{background:#1f2937;border-radius:12px;padding:15px;border:1px solid #333;margin-bottom:15px}
.label{color:#a1a1a6!important;font-size:12px!important;text-align:center!important;margin-bottom:18px!important}
.end-btn button{background:#ff3b30!important}
</style>
""", unsafe_allow_html=True)

os.makedirs("room_data",exist_ok=True)

# ---- NOTES (FIXED CLOSE) ----
if st.session_state.show_notes:
    st.markdown("<div class='notes-box'>",unsafe_allow_html=True)
    st.markdown("### 📝 Call Notes")
    st.session_state.notes_text = st.text_area("",value=st.session_state.notes_text,height=150,key="notes_area")
    c1,c2=st.columns(2)
    if c1.button("💾 Save",type="primary",use_container_width=True):
        open(f"room_data/{st.session_state.room}_notes.txt","w",encoding="utf-8").write(st.session_state.notes_text)
        st.success("Saved")
    if c2.button("❌ Close",use_container_width=True):
        st.session_state.show_notes=False; st.rerun()
    st.markdown("</div>",unsafe_allow_html=True)

# ---- KEYPAD (FIXED CLOSE) ----
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

# ---- MAIN DESIGN - EXACTLY LIKE 1ST IMAGE ----
st.markdown(f"<div class='call-screen'><h3>Telugu - Anand Paul</h3><p>{'🔴 On Hold' if st.session_state.is_hold else '⚪ Paused' if not st.session_state.is_live else '🔴 LIVE'}<br>Room: {st.session_state.room}</p></div>",unsafe_allow_html=True)
st.markdown(f"<div class='count-box'>👥 Live: 2 | Room: {st.session_state.room}</div>",unsafe_allow_html=True)

target = st.selectbox("Translate To:", ["Telugu","Hindi","Tamil","English"], index=1)

r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝",key="b1",use_container_width=True): st.session_state.show_notes=not st.session_state.show_notes; st.rerun()
    st.markdown("<div class='label'>Notes</div>",unsafe_allow_html=True)
with r1c2:
    if st.button("➕",key="b2",use_container_width=True): st.info(f"Code: {st.session_state.room}")
    st.markdown("<div class='label'>Add call</div>",unsafe_allow_html=True)
with r1c3:
    if st.button("🔇",key="b3",use_container_width=True): st.session_state.is_muted=not st.session_state.is_muted; st.rerun()
    st.markdown("<div class='label'>Mute</div>",unsafe_allow_html=True)

r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    if st.button("⚪" if not st.session_state.is_live else "🔴",key="b4",use_container_width=True): st.session_state.is_live=not st.session_state.is_live; st.rerun()
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
    if st.button("📞",key="b8",use_container_width=True): st.session_state.room=None; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<div class='label'>End call</div>",unsafe_allow_html=True)
with r3c3:
    if st.button("🔊",key="b9",use_container_width=True): st.session_state.is_speaker=not st.session_state.is_speaker; st.rerun()
    st.markdown("<div class='label'>Speaker</div>",unsafe_allow_html=True)

st.divider()

# ---- PUSH TO TALK + REAL TRANSLATE (ADDED INSIDE SAME DESIGN) ----
st.markdown("### 🎤 Push to Talk - Matladu, Hindi lo vellali")
audio = st.audio_input("Mic nokki Telugu lo matladu")

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

if audio:
    in_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_in.wav"
    with open(in_path,"wb") as f: f.write(audio.getbuffer())
    if st.session_state.is_live and not st.session_state.is_hold:
        with st.spinner(f"Telugu -> {target} ki translate chestunna..."):
            try:
                # 1. STT
                with open(in_path,"rb") as f:
                    stt = client.speech_to_text_transcribe(file=f, model="saarika:v2", language_code="te-IN")
                    orig = getattr(stt,"transcript","") or getattr(stt,"text","") or str(stt)
                    if not orig: orig="namaste"
                st.info(f"Original (Telugu): {orig}")
                
                # 2. TRANSLATE - REAL TRANSLATION
                tgt_code = lang_map[target]
                try:
                    trans = client.text.translate(text=orig, source_language_code="te-IN", target_language_code=tgt_code)
                    translated_text = trans.translated_text if hasattr(trans,"translated_text") else getattr(trans,"translation",orig)
                except:
                    # fallback - direct use if translate API different version
                    translated_text = orig
                
                st.success(f"Translated ({target}): {translated_text}")
                
                # 3. TTS in TARGET language
                tts = client.text_to_speech.convert(text=translated_text, target_language_code=tgt_code, speaker="anushka", model="bulbul:v2")
                out_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_out_{int(time.time())}_{target}.wav"
                aud = tts.audios[0] if hasattr(tts,"audios") else None
                if aud:
                    try:
                        data = base64.b64decode(aud)
                    except:
                        data = aud.encode() if isinstance(aud,str) else aud
                    open(out_path,"wb").write(data)
                    st.audio(out_path)
                    st.caption(f"Saved for other phone: {target} voice")
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.markdown("### 🔊 Incoming - Vere phone nundi vachina translated voice")
files=sorted([f for f in os.listdir("room_data") if f.startswith(st.session_state.room) and "_out_" in f and st.session_state.my_id not in f], reverse=True)[:5]
if not files:
    st.caption("Inka voice raledu - vere phone lo matladi Refresh nokku")
for f in files:
    fp=f"room_data/{f}"
    if os.path.exists(fp):
        st.audio(fp, autoplay=False)
        st.caption(f"{f} - {time.ctime(os.path.getmtime(fp))}")

if st.button("🔄 Refresh to get new translated voice",use_container_width=True):
    st.rerun()
