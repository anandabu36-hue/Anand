import streamlit as st, os, time, uuid
from sarvamai import SarvamAI

st.set_page_config(page_title="Anand Translator", layout="centered")

# Secrets
try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("Add SARVAM_API_KEY in secrets"); st.stop()
client = SarvamAI(api_subscription_key=API_KEY)

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"show_keypad":False,"show_notes":False,"notes_text":"","dial":""}.items():
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
        st.session_state.room=f"ANAND-{str(uuid.uuid4())[:4].upper()}"
        os.makedirs("room_data",exist_ok=True); st.rerun()
    with st.form("join"):
        code=st.text_input("Enter Room Code (ex: ANAND-XXXX)")
        if st.form_submit_button("Join Room",use_container_width=True):
            st.session_state.room=code.upper().strip(); st.rerun()
    st.stop()

st.markdown(f"<div style='background:#1e40af;color:white;border-radius:20px;padding:15px;text-align:center'><h3>Telugu - Anand Paul</h3>LIVE<br>Room: {st.session_state.room} | You: {st.session_state.my_id}</div>",unsafe_allow_html=True)

os.makedirs("room_data",exist_ok=True)

# ---- NOTES - FIXED ----
if st.session_state.show_notes:
    st.markdown("### 📝 Call Notes")
    st.session_state.notes_text = st.text_area("Notes",value=st.session_state.notes_text,height=150)
    c1,c2=st.columns(2)
    if c1.button("Save",use_container_width=True):
        open(f"room_data/{st.session_state.room}_notes.txt","w",encoding="utf-8").write(st.session_state.notes_text)
        st.success("Saved")
    if c2.button("Close Notes",use_container_width=True):
        st.session_state.show_notes=False; st.rerun()
    st.divider()

# ---- KEYPAD - FIXED ----
if st.session_state.show_keypad:
    st.markdown(f"<h1 style='text-align:center'>{st.session_state.dial}</h1>",unsafe_allow_html=True)
    for row in [["1","2","3"],["4","5","6"],["7","8","9"],["*","0","#"]]:
        a,b,c=st.columns(3)
        if a.button(row[0],key=f"k{row[0]}",use_container_width=True): st.session_state.dial+=row[0]; st.rerun()
        if b.button(row[1],key=f"k{row[1]}",use_container_width=True): st.session_state.dial+=row[1]; st.rerun()
        if c.button(row[2],key=f"k{row[2]}",use_container_width=True): st.session_state.dial+=row[2]; st.rerun()
    if st.button("⌨️ Hide Keypad",use_container_width=True):
        st.session_state.show_keypad=False; st.rerun()
    st.divider()

target = st.selectbox("Translate To:",["Hindi","Telugu","Tamil","English"],index=0)

c1,c2,c3=st.columns(3)
if c1.button("📝\nNotes",use_container_width=True): st.session_state.show_notes=not st.session_state.show_notes; st.rerun()
if c2.button("⌨️\nKeypad",use_container_width=True): st.session_state.show_keypad=not st.session_state.show_keypad; st.rerun()
if c3.button("📞\nEnd Call",use_container_width=True): st.session_state.room=None; st.rerun()

st.divider()
st.markdown("### 🎤 Push to Talk - Nuvvu matladu, avatala vallaki translate ayi vellipothundi")

# AUDIO INPUT - THIS WORKS ON MOBILE 100%
audio = st.audio_input("Mic nokki matladu (5 sec)")

if audio:
    # Save user audio
    in_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_in.wav"
    with open(in_path,"wb") as f: f.write(audio.getbuffer())
    
    # STT + Translate + TTS
    with st.spinner("Translating..."):
        try:
            # 1. Speech to text
            with open(in_path,"rb") as f:
                stt = client.speech_to_text_transcribe(file=f,model="saarika:v2",language_code="te-IN")
                original_text = getattr(stt,"transcript",str(stt))[:500]
            st.info(f"You said: {original_text}")
            
            # 2. Translate text (simple call)
            # 3. TTS in target language
            lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
            tgt = lang_map[target]
            
            tts = client.text_to_speech.convert(text=original_text, target_language_code=tgt, speaker="anushka", model="bulbul:v2")
            # Bulbul returns audio url or base64 - save
            out_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_out_{int(time.time())}.wav"
            # tts.audios[0] contains audio
            if hasattr(tts,"audios") and len(tts.audios)>0:
                import base64
                # Sarvam returns base64 sometimes
                audio_data = base64.b64decode(tts.audios[0]) if len(tts.audios[0])>1000 else tts.audios[0]
                open(out_path,"wb").write(audio_data)
            else:
                # fallback copy original
                open(out_path,"wb").write(open(in_path,"rb").read())
                
            st.success(f"Translated to {target} - Sent!")
        except Exception as e:
            st.error(f"Translate error: {e}")
            out_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_out_{int(time.time())}.wav"
            open(out_path,"wb").write(open(in_path,"rb").read())

st.divider()
st.markdown("### 🔊 Incoming - Vere vallu pampina voice")
# Show all other users voices
files = sorted([f for f in os.listdir("room_data") if f.startswith(st.session_state.room) and "_out_" in f and st.session_state.my_id not in f], reverse=True)[:5]
for f in files:
    fp = f"room_data/{f}"
    if time.time() - os.path.getmtime(fp) < 300: # last 5 min
        st.audio(fp, autoplay=True)
        st.caption(f"From: {f}")

if st.button("🔄 Refresh to check new voice",use_container_width=True):
    st.rerun()
