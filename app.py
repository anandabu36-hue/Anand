import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, os, time, uuid, glob, wave, tempfile

API_KEY = st.secrets["SARVAM_API_KEY"]
client = SarvamAI(api_subscription_key=API_KEY) if API_KEY else None

LANG_MAP = {"Hindi": "hi-IN", "Telugu": "te-IN", "Tamil": "ta-IN", "English": "en-IN", "Kannada": "kn-IN",
            "Malayalam": "ml-IN"}
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

st.set_page_config(page_title="Anand Live - Direct START Live", layout="centered")

if "auth" not in st.session_state: st.session_state.auth = False
if "room" not in st.session_state: st.session_state.room = None
if "live" not in st.session_state: st.session_state.live = False
if "my_lang" not in st.session_state: st.session_state.my_lang = "Telugu"
if "last_heard" not in st.session_state: st.session_state.last_heard = ""

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center'>📞 Anand Live Translator</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Unlock", use_container_width=True, type="primary"):
        if pwd == "meAbu":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Wrong!")
    st.stop()

if not st.session_state.room:
    st.markdown(
        """<div style='background: linear-gradient(180deg, #4facfe 0%, #1a237e 100%); border-radius:30px; padding:30px; color:white; text-align:center;'><h2>Anand - Live Translator</h2><p>START = Live, STOP = Mute</p></div>""",
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📞 Create Call", use_container_width=True, type="primary"):
            st.session_state.room = f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        code = st.text_input("Room Code:")
        if st.button("Join Call", use_container_width=True):
            if code:
                st.session_state.room = code.upper()
                st.rerun()
    st.stop()

# --- HEADER ---
st.markdown(
    f"<div style='background:#111;color:white;padding:15px;border-radius:15px;text-align:center'><h3>Room: {st.session_state.room}</h3><p>{'🔴 LIVE - Matladu, Direct ga veltundi' if st.session_state.live else '⚪ STOPPED'}</p></div>",
    unsafe_allow_html=True)

st.session_state.my_lang = st.selectbox("Nee Bhasha (Avatali voice neeku ee bhasha lo ravali)", list(LANG_MAP.keys()),
                                        index=1)
my_code = LANG_MAP[st.session_state.my_lang]

# --- START / STOP ONLY ---
c1, c2 = st.columns(2)
with c1:
    if st.button("▶️ START", use_container_width=True, type="primary", disabled=st.session_state.live):
        st.session_state.live = True
        st.rerun()
with c2:
    if st.button("⏹️ STOP", use_container_width=True, disabled=not st.session_state.live):
        st.session_state.live = False
        st.rerun()

st.divider()

# --- WEBRTC ---
# Live ayithe ne audio capture
webrtc_ctx = webrtc_streamer(
    key=f"direct-live-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": False, "audio": True},
)

# --- AUTO LIVE TRANSLATION WHEN LIVE IS ON ---
if st.session_state.live and client:
    st.markdown("### 🔴 LIVE ON - Matladu, Auto Translate Avuthundi...")

    # Use audio_input for reliable STT - WebRTC raw audio ni direct ga vadadam kastam, so simple trick
    # WebRTC call ON lo untundi, kani translation ki manam ikkada record chestham - Idi 3 sec lo auto trigger avuthundi
    audio = st.audio_input("🎤 LIVE - Matladu (3 sec matladagane auto send avuthundi)", key=f"live_{time.time()}")

    if audio:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio.getvalue())
            path = tmp.name
        try:
            with open(path, "rb") as f:
                stt = client.speech_to_text.transcribe(file=f, model="saarika:v2.5", language_code="unknown")

            transcript = (stt.transcript or "").strip()
            if transcript:
                st.info(f"Nuvvu: {transcript}")
                # Save for other person - Other person language ki convert avvadaniki
                os.makedirs("room_data", exist_ok=True)
                with open(f"room_data/{st.session_state.room}_live.txt", "w", encoding="utf-8") as f:
                    f.write(f"{stt.language_code}|{transcript}|{time.time()}")

                st.toast(f"✅ Sent to Room {st.session_state.room}!", icon="📤")
                # Auto rerun to ready for next sentence
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Voice clear ga ledu - Malli matladu!")
        except Exception as e:
            if "Input text must not be empty" not in str(e):
                st.error(f"{e}")
        finally:
            if os.path.exists(path): os.remove(path)
    else:
        st.caption("Mic ON lo undi - Matladu - Record complete avagane automatic ga avatali vaallaki velthundi")

else:
    if not st.session_state.live:
        st.warning("⏹️ STOP lo unnav - START nokki matladu")

# --- AUTO RECEIVE FROM OTHER PERSON - LIVE ---
st.markdown("### 📥 Avatali nundi LIVE")

# Auto refresh logic
live_file = f"room_data/{st.session_state.room}_live.txt"
if os.path.exists(live_file):
    try:
        with open(live_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "|" in content:
            src_lang, text, ts = content.split("|")
            # Don't play my own sent message again
            if text != st.session_state.last_heard and text.strip():
                # Check if this is not my own recent message (by comparing timestamp maybe)
                # For simplicity - If source lang != my target and text is new
                if src_lang != my_code:
                    st.info(f"Avatali ({src_lang}): {text}")
                    # DIRECT TRANSLATE TO MY LANGUAGE
                    trans = client.text.translate(input=text, source_language_code=src_lang,
                                                  target_language_code=my_code, model="mayura:v1")
                    translated = (trans.translated_text or "").strip()
                    if translated:
                        st.success(f"Neeku ({st.session_state.my_lang}): {translated}")
                        tts = client.text_to_speech.convert(language_code=my_code, text=translated, model="bulbul:v2",
                                                            speaker="anushka")
                        from sarvamai.play import save

                        save(tts, "other.wav")
                        st.audio("other.wav", autoplay=True)
                        st.session_state.last_heard = text
                        st.toast("🔊 Avatali nundi LIVE Voice vachindi!", icon="📥")
    except Exception as e:
        st.caption(f"Waiting... {e}")

# Auto check every 3 seconds - Button nokkakunda auto ravali ante
if st.session_state.live:
    time.sleep(3)
    st.rerun()

st.caption(f"Room: {st.session_state.room} | START=Live | STOP=Mute | No extra button")
