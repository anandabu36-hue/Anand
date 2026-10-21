import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av, tempfile, os, time, uuid

API_KEY = st.secrets["SARVAM_API_KEY"]
client = SarvamAI(api_subscription_key=API_KEY) if API_KEY else None

LANG_MAP = {"Hindi": "hi-IN", "Telugu": "te-IN", "Tamil": "ta-IN", "English": "en-IN", "Kannada": "kn-IN",
            "Malayalam": "ml-IN"}
# Speaker per language - cost save
SPEAKER_MAP = {"hi-IN": "anushka", "te-IN": "anushka", "ta-IN": "abhilash", "en-IN": "anushka", "kn-IN": "anushka",
               "ml-IN": "anushka"}

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Live Translator - Direct S2S", layout="centered")

if "auth" not in st.session_state: st.session_state.auth = False
if "room" not in st.session_state: st.session_state.room = None
if "mute" not in st.session_state: st.session_state.mute = False
if "hold" not in st.session_state: st.session_state.hold = False
if "page" not in st.session_state: st.session_state.page = "call"
if "notes" not in st.session_state: st.session_state.notes = ""

if not st.session_state.auth:
    st.markdown(
        "<h2 style='text-align:center'>📞 Anand Live Translator</h2><p style='text-align:center'>FREE Real Call - Direct Voice</p>",
        unsafe_allow_html=True)
    pwd = st.text_input("Password ", type="password")
    if st.button("Unlock", use_container_width=True, type="primary"):
        if pwd == "meAbu":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Wrong!")
    st.stop()

if st.session_state.hold:
    st.markdown(
        "<div style='background:#111;color:white;text-align:center;padding:80px;border-radius:30px;'><h1>⏸️ Call on Hold</h1></div>",
        unsafe_allow_html=True)
    if st.button("▶️ Resume", use_container_width=True, type="primary"):
        st.session_state.hold = False
        st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("""
    <div style='background: linear-gradient(180deg, #4facfe 0%, #1a237e 100%); border-radius:30px; padding:30px; color:white; text-align:center;'>
        <h2>Anand - Live Translator</h2><p>FREE Internet Call - Direct Speech to Speech</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create New Call Link", use_container_width=True, type="primary"):
            st.session_state.room = f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.rerun()
    with c2:
        code = st.text_input("Room Code:")
        if st.button("Join Call", use_container_width=True):
            if code:
                st.session_state.room = code.upper()
                st.rerun()
    st.stop()

st.markdown(f"""
<div style='background: linear-gradient(180deg, #4facfe 0%, #1a237e 100%); border-radius:30px; padding:20px; color:white; text-align:center;'>
    <h3>Anand - Live Translator</h3>
    <p>Room: {st.session_state.room} | {'🔇 Muted' if st.session_state.mute else '🌏 Direct S2S ON'}</p>
</div>
""", unsafe_allow_html=True)

st.write("")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("📝",
                 use_container_width=True): st.session_state.page = "notes" if st.session_state.page != "notes" else "call"
    st.caption("Notes")
with c2:
    if st.button("➕", use_container_width=True): st.toast(f"Share: {st.session_state.room}")
    st.caption("Add call")
with c3:
    if st.button("🔇" if not st.session_state.mute else "🎙️",
                 use_container_width=True): st.session_state.mute = not st.session_state.mute
    st.caption("Mute" if not st.session_state.mute else "Unmute")

b1, b2, b3 = st.columns([1, 1, 1])
with b2:
    if st.button("📞", use_container_width=True, type="primary"):
        st.session_state.room = None
        st.session_state.auth = False
        st.rerun()

st.divider()
st.markdown("### 🌏 DIRECT Speech to Speech - LIVE")
target = st.selectbox("Neeku ye bhasha lo vinipinchali?", list(LANG_MAP.keys()), index=1)
tgt_code = LANG_MAP[target]
st.success(f"Room: {st.session_state.room} - Nuvvu matladithe {target} lo VOICE vastundi!")


def audio_callback(frame: av.AudioFrame):
    return frame if not st.session_state.mute else frame


webrtc_ctx = webrtc_streamer(
    key=f"call-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": False, "audio": True},
    audio_frame_callback=audio_callback,
    async_processing=True,
)

st.markdown("#### 🎤 Live Translation - Direct Voice")
st.caption("2-3 sec clear ga matladu")

if not client:
    st.error("API Key missing")
else:
    audio = st.audio_input("Record chey - Direct S2S")
    if audio and not st.session_state.mute:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio.getvalue())
            path = tmp.name
        try:
            with st.spinner(f"Direct ga {target} ki marchuthunna..."):
                with open(path, "rb") as f:
                    stt = client.speech_to_text.transcribe(file=f, model="saarika:v2.5", language_code="unknown")

                # === FINAL FIX FOR YOUR ERROR ===
                transcript = ""
                if hasattr(stt, 'transcript') and stt.transcript:
                    transcript = stt.transcript.strip()

                if not transcript:
                    st.warning("🎤 Voice clear ga ledu Anand - Mic daggara petti 2-3 sec peddaga matladu!")
                else:
                    st.info(f"Caller ({stt.language_code}): {transcript}")

                    # Translate
                    trans = client.text.translate(input=transcript, source_language_code=stt.language_code,
                                                  target_language_code=tgt_code, model="mayura:v1")
                    translated_text = (trans.translated_text or "").strip()

                    if not translated_text:
                        st.warning("Translation raaledu - Malli try chey")
                    else:
                        st.success(f"You ({target}): {translated_text}")

                        # TTS
                        speaker = SPEAKER_MAP.get(tgt_code, "anushka")
                        tts = client.text_to_speech.convert(language_code=tgt_code, text=translated_text,
                                                            model="bulbul:v2", speaker=speaker)
                        from sarvamai.play import save

                        save(tts, "out.wav")
                        st.audio("out.wav", autoplay=True)
                        st.toast(f"✅ {target} Voice Ready!", icon="🔊")
        except Exception as e:
            # This is the error you got - now we handle it gracefully
            if "Input text must not be empty" in str(e):
                st.warning("🎤 Voice empty - Malli konchem peddaga, clear ga matladu!")
            else:
                st.error(f"Error: {e}")
        finally:
            if os.path.exists(path): os.remove(path)
