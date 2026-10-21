import streamlit as st
from sarvamai import SarvamAI
import os, time, uuid, tempfile
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

API_KEY = st.secrets["SARVAM_API_KEY"]
client = SarvamAI(api_subscription_key=API_KEY) if API_KEY else None

LANG_MAP = {"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN","Kannada":"kn-IN","Malayalam":"ml-IN"}
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

st.set_page_config(page_title="Anand Live - Laptop to Phone LIVE", layout="centered")

if "auth" not in st.session_state: st.session_state.auth = False
if "room" not in st.session_state: st.session_state.room = None
if "live" not in st.session_state: st.session_state.live = False
if "my_lang" not in st.session_state: st.session_state.my_lang = "Telugu"
if "last_id" not in st.session_state: st.session_state.last_id = ""

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>📞 Anand Live</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Unlock", use_container_width=True, type="primary"):
        if pwd == "meAbu":
            st.session_state.auth = True
            st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("""<div style='background:#4facfe;border-radius:20px;padding:20px;color:white;text-align:center'><h3>Laptop -> Phone LIVE</h3></div>""", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Create Call", use_container_width=True, type="primary"):
            st.session_state.room = f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        code = st.text_input("Room Code Join:")
        if st.button("Join", use_container_width=True):
            if code:
                st.session_state.room = code.upper()
                st.rerun()
    st.stop()

st.markdown(f"<div style='background:black;color:white;padding:10px;border-radius:10px;text-align:center'>Room: {st.session_state.room} | {'🔴 LIVE' if st.session_state.live else '⚪ STOP'}</div>", unsafe_allow_html=True)

st.session_state.my_lang = st.selectbox("Nee phone ki ye bhasha lo kavali?", list(LANG_MAP.keys()), index=1)
my_code = LANG_MAP[st.session_state.my_lang]

c1,c2 = st.columns(2)
with c1:
    if st.button("▶️ START - Nenu Matladutha", use_container_width=True, type="primary", disabled=st.session_state.live):
        st.session_state.live = True
        st.rerun()
with c2:
    if st.button("⏹️ STOP", use_container_width=True, disabled=not st.session_state.live):
        st.session_state.live = False
        st.rerun()

webrtc_streamer(key=f"call-{st.session_state.room}", mode=WebRtcMode.SENDRECV, rtc_configuration=RTC_CONFIG, media_stream_constraints={"video":False,"audio":True})

st.divider()

# ============ SENDER PART - LAPTOP LO MATLADITHE ============
if st.session_state.live:
    st.markdown("### 🎤 LIVE - Laptop lo Matladu")
    # key change cheste malli record cheyadaniki ready avuthundi
    audio = st.audio_input("Matladu - Aapeyagane Phone ki velthundi", key=f"rec_{time.time()}")
    
    if audio:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio.getvalue())
            path = tmp.name
        try:
            with open(path, "rb") as f:
                stt = client.speech_to_text.transcribe(file=f, model="saarika:v2.5", language_code="unknown")
            txt = (stt.transcript or "").strip()
            if txt:
                os.makedirs("room_data", exist_ok=True)
                # Idhi save chesthe phone lo auto vastundi
                with open(f"room_data/{st.session_state.room}.txt", "w", encoding="utf-8") as f:
                    f.write(f"{stt.language_code}|{txt}|{str(uuid.uuid4())}")
                st.success(f"Sent: {txt} -> Phone ki vellindi!")
                time.sleep(0.5)
                st.rerun() # Malli next sentence ki ready
        except Exception as e:
            st.error(str(e))
        finally:
            if os.path.exists(path): os.remove(path)

# ============ RECEIVER PART - PHONE LO VINIPINCHALI ============
st.markdown("### 📥 Phone lo Vinipinchali ante - Ikada vastundi")

live_file = f"room_data/{st.session_state.room}.txt"
if os.path.exists(live_file):
    try:
        with open(live_file, "r", encoding="utf-8") as f:
            data = f.read()
        src_lang, text, uid = data.split("|")
        
        # Kotha message ayithe ne play chey
        if uid != st.session_state.last_id and text.strip():
            st.info(f"Laptop nundi ({src_lang}): {text}")
            
            # Phone bhasha lo ki marchu
            if src_lang != my_code:
                trans = client.text.translate(input=text, source_language_code=src_lang, target_language_code=my_code, model="mayura:v1")
                translated = trans.translated_text
                
                tts = client.text_to_speech.convert(language_code=my_code, text=translated, model="bulbul:v2", speaker="anushka")
                from sarvamai.play import save
                save(tts, "live_out.wav")
                st.success(f"Phone lo ({st.session_state.my_lang}): {translated}")
                st.audio("live_out.wav", autoplay=True)
                st.session_state.last_id = uid
            else:
                st.write(text)
    except:
        pass
else:
    st.caption("Inka laptop nundi voice raaledu... Laptop lo START noki matladu")

# Auto refresh - Phone lo automatic ga 2 sec ki check chestundi
if True:
    time.sleep(2)
    st.rerun()
