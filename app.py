import base64
import html
import os
import queue
import time
import uuid
import wave

import numpy as np
import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer
from supabase import create_client


st.set_page_config(
    page_title="Anand Live Translator",
    page_icon="📞",
    layout="centered",
)

LANGUAGES = {
    "Telugu": "te-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "English": "en-IN",
}
DATA_DIR = os.path.join(os.getcwd(), "room_data")
os.makedirs(DATA_DIR, exist_ok=True)

required_secrets = ("SARVAM_API_KEY", "SUPABASE_URL", "SUPABASE_KEY")
missing_secrets = [key for key in required_secrets if not st.secrets.get(key)]
if missing_secrets:
    st.error("Missing Streamlit Secrets: " + ", ".join(missing_secrets))
    st.stop()

sarvam = SarvamAI(api_subscription_key=st.secrets["SARVAM_API_KEY"])
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)
rtc_config = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

DEFAULT_STATE = {
    "auth": False,
    "room": None,
    "my_id": uuid.uuid4().hex[:8],
    "my_listen": "Telugu",
    "buffer": [],
    "audio_sample_rate": 48000,
    "last_speech": 0.0,
    "is_speaking": False,
    "auto_lock": False,
    "call_start": 0.0,
    "last_message_id": 0,
    "incoming_history": [],
    "last_error": "",
    "debug_audio_frames": 0,
    "debug_peak": 0.0,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

app_password = st.secrets.get("APP_PASSWORD", "")
if app_password and not st.session_state.auth:
    st.title("🔒 Anand Live Translator")
    with st.form("login_form"):
        password = st.text_input("App password", type="password")
        submitted = st.form_submit_button("Unlock", use_container_width=True)

    if submitted:
        if password == app_password:
            st.session_state.auth = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()

st.session_state.auth = True


def create_room(room_code):
    result = supabase.table("call_rooms").insert(
        {
            "room_code": room_code,
            "created_by": st.session_state.my_id,
            "is_active": True,
        }
    ).execute()
    return bool(result.data)


def room_exists(room_code):
    result = (
        supabase.table("call_rooms")
        .select("room_code")
        .eq("room_code", room_code)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def transcribe_audio(wav_path):
    with open(wav_path, "rb") as audio_file:
        response = sarvam.speech_to_text.transcribe(
            file=audio_file,
            model="saaras:v3",
        )

    transcript = getattr(response, "transcript", "")
    language_code = getattr(response, "language_code", None)
    if isinstance(response, dict):
        transcript = transcript or response.get("transcript", "")
        language_code = language_code or response.get("language_code")

    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError(f"Speech-to-text returned no transcript: {response}")
    return transcript.strip(), language_code


def publish_message(text, source_language):
    language_code = (
        source_language if source_language in LANGUAGES.values() else None
    )
    result = supabase.table("call_messages").insert(
        {
            "room_code": st.session_state.room,
            "sender_id": st.session_state.my_id,
            "original_text": text,
            "source_language": language_code,
        }
    ).execute()
    if not result.data:
        raise RuntimeError("Supabase did not confirm the message was saved.")


def process_buffer():
    if st.session_state.auto_lock:
        return

    chunks = st.session_state.buffer
    sample_rate = int(st.session_state.audio_sample_rate)
    if not chunks:
        st.session_state.is_speaking = False
        return

    audio = np.concatenate(chunks).astype(np.int16, copy=False)
    st.session_state.buffer = []
    st.session_state.is_speaking = False

    if audio.size < int(sample_rate * 0.25):
        return

    st.session_state.auto_lock = True
    wav_path = os.path.join(DATA_DIR, f"{uuid.uuid4().hex}.wav")
    try:
        with wave.open(wav_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())

        transcript, source_language = transcribe_audio(wav_path)
        publish_message(transcript, source_language)
        st.session_state.last_error = ""
        st.toast(f"Speech sent: {transcript[:80]}", icon="✅")
    except Exception as exc:
        st.session_state.last_error = f"{type(exc).__name__}: {exc}"
    finally:
        st.session_state.auto_lock = False
        if os.path.exists(wav_path):
            os.remove(wav_path)


def translate_text(text, target_language, source_language=None):
    supported = set(LANGUAGES.values())
    source_code = (
        source_language
        if source_language in supported and source_language != target_language
        else "auto"
    )
    response = sarvam.text.translate(
        input=text,
        source_language_code=source_code,
        target_language_code=target_language,
        model="mayura:v1",
    )
    translated = getattr(response, "translated_text", None)
    if not translated and isinstance(response, dict):
        translated = response.get("translated_text")
    if not isinstance(translated, str) or not translated.strip():
        raise ValueError(f"Translation returned no text: {response}")
    return translated.strip()


def generate_speech(text, target_language, output_path):
    response = sarvam.text_to_speech.convert(
        text=text,
        language_code=target_language,
        speaker="anushka",
        model="bulbul:v3",
        output_audio_codec="wav",
    )
    audios = getattr(response, "audios", None)
    if not audios and isinstance(response, dict):
        audios = response.get("audios")
    if not audios or not audios[0]:
        raise ValueError(f"Text-to-speech returned no audio: {response}")
    with open(output_path, "wb") as audio_file:
        audio_file.write(base64.b64decode(audios[0]))


def get_new_messages():
    result = (
        supabase.table("call_messages")
        .select(
            "id,room_code,sender_id,original_text,source_language,created_at"
        )
        .eq("room_code", st.session_state.room)
        .gt("id", st.session_state.last_message_id)
        .order("id")
        .limit(50)
        .execute()
    )
    return result.data or []


st.markdown(
    """<div style="background:linear-gradient(135deg,#667eea,#764ba2);
    padding:22px;border-radius:18px;color:white;text-align:center">
    <h2>📞 Anand Live Translator</h2>
    <p>Speak your language. Understand theirs.</p></div>""",
    unsafe_allow_html=True,
)

if not st.session_state.room:
    left, right = st.columns(2)
    with left:
        if st.button("📞 Create Call", type="primary", use_container_width=True):
            room_code = "ANAND-" + uuid.uuid4().hex[:6].upper()
            try:
                if create_room(room_code):
                    st.session_state.room = room_code
                    st.session_state.call_start = time.time()
                    st.session_state.last_message_id = 0
                    st.session_state.incoming_history = []
                    st.rerun()
                st.error("Room was not created. Please try again.")
            except Exception as exc:
                st.error(f"Supabase room creation failed: {exc}")

    with right:
        with st.form("join_room"):
            room_code = st.text_input("Room code").strip().upper()
            if st.form_submit_button("Join Call", use_container_width=True):
                if not room_code:
                    st.warning("Enter a room code.")
                else:
                    try:
                        if room_exists(room_code):
                            st.session_state.room = room_code
                            st.session_state.call_start = time.time()
                            st.session_state.last_message_id = 0
                            st.session_state.incoming_history = []
                            st.rerun()
                        st.error("Invalid room code or the call has ended.")
                    except Exception as exc:
                        st.error(f"Room validation failed: {exc}")

    st.info("Share the room code. Both participants must use this deployed app.")
    st.stop()

elapsed = max(0, int(time.time() - st.session_state.call_start))
mins, secs = divmod(elapsed, 60)
st.markdown(f"**Room:** `{st.session_state.room}` · **Call time:** {mins:02d}:{secs:02d}")
st.caption(f"Your participant ID: {st.session_state.my_id}")

st.session_state.my_listen = st.selectbox(
    "🌐 I want to hear in:",
    list(LANGUAGES),
    index=list(LANGUAGES).index(st.session_state.my_listen),
)
target_code = LANGUAGES[st.session_state.my_listen]

ctx = webrtc_streamer(
    key=f"mic-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=rtc_config,
    media_stream_constraints={"video": False, "audio": True},
    audio_receiver_size=1024,
    async_processing=True,
)


@st.fragment(run_every=0.2)
def capture_and_process_audio():
    if not ctx or not ctx.state.playing or not ctx.audio_receiver:
        st.caption("Start the microphone when your browser asks for permission.")
        return

    try:
        frames = ctx.audio_receiver.get_frames(timeout=0.05)
    except queue.Empty:
        frames = []
    except Exception as exc:
        st.session_state.last_error = (
            f"Audio receiver: {type(exc).__name__}: {exc}"
        )
        frames = []

    for frame in frames:
        st.session_state.debug_audio_frames += 1
        frame_rate = getattr(frame, "sample_rate", None)
        if frame_rate:
            st.session_state.audio_sample_rate = int(frame_rate)

        values = frame.to_ndarray()
        if values.ndim == 2:
            pcm = values.astype(np.float32).mean(axis=0)
        else:
            pcm = values.astype(np.float32).flatten()

        if np.issubdtype(values.dtype, np.floating):
            peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
            if peak <= 1.0:
                pcm *= 32767.0

        pcm = np.clip(pcm, -32768, 32767).astype(np.int16)
        rms = (
            float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
            if pcm.size
            else 0.0
        )
        st.session_state.debug_peak = max(st.session_state.debug_peak, rms)

        if rms > 250:
            st.session_state.last_speech = time.time()
            st.session_state.is_speaking = True
            st.session_state.buffer.append(pcm)
        elif st.session_state.is_speaking:
            st.session_state.buffer.append(pcm)

    if (
        st.session_state.is_speaking
        and time.time() - st.session_state.last_speech > 1.2
    ):
        process_buffer()

    st.caption(
        f"Microphone active · audio frames: "
        f"{st.session_state.debug_audio_frames} · "
        f"buffer chunks: {len(st.session_state.buffer)}"
    )


capture_and_process_audio()

if st.session_state.last_error:
    st.error("Speech processing failed: " + st.session_state.last_error)

st.divider()
st.subheader("🌐 Incoming translated speech")


@st.fragment(run_every=2)
def incoming_messages():
    try:
        messages = get_new_messages()
    except Exception as exc:
        st.error(f"Could not read messages from Supabase: {exc}")
        return

    new_history = []
    for message in messages:
        message_id = int(message["id"])
        st.session_state.last_message_id = max(
            st.session_state.last_message_id, message_id
        )
        if message.get("sender_id") == st.session_state.my_id:
            continue

        original = str(message.get("original_text") or "").strip()
        if not original:
            continue

        audio_path = os.path.join(
            DATA_DIR,
            f"translated_{st.session_state.my_id}_{message_id}_{target_code}.wav",
        )
        try:
            translated = translate_text(
                original,
                target_code,
                message.get("source_language"),
            )
            if not os.path.exists(audio_path):
                generate_speech(translated, target_code, audio_path)
            new_history.append(
                {
                    "id": message_id,
                    "original": original,
                    "translated": translated,
                    "audio_path": audio_path,
                    "autoplay": True,
                }
            )
        except Exception as exc:
            new_history.append(
                {
                    "id": message_id,
                    "original": original,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    if new_history:
        st.session_state.incoming_history.extend(new_history)
        st.session_state.incoming_history = st.session_state.incoming_history[-20:]

    if not st.session_state.incoming_history:
        st.caption("Waiting for the other participant to speak...")
        return

    for item in reversed(st.session_state.incoming_history):
        st.markdown(
            '<div style="background:#20202b;color:white;padding:12px;'
            'border-radius:12px"><b>Original speech</b><br>'
            + html.escape(item["original"])
            + "</div>",
            unsafe_allow_html=True,
        )
        if item.get("error"):
            st.error("Translation/audio generation failed: " + item["error"])
            continue

        st.markdown(f"**Translation ({st.session_state.my_listen}):**")
        st.write(item["translated"])
        st.audio(
            item["audio_path"],
            format="audio/wav",
            autoplay=item.pop("autoplay", False),
        )


incoming_messages()

st.divider()
left, right = st.columns(2)
with left:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
with right:
    if st.button("📞 End Call", type="primary", use_container_width=True):
        try:
            supabase.table("call_rooms").update(
                {"is_active": False}
            ).eq("room_code", st.session_state.room).execute()
        except Exception as exc:
            st.warning(f"Call ended here, but room status update failed: {exc}")

        st.session_state.room = None
        st.session_state.buffer = []
        st.session_state.is_speaking = False
        st.session_state.call_start = 0.0
        st.session_state.last_message_id = 0
        st.session_state.incoming_history = []
        st.session_state.debug_audio_frames = 0
        st.session_state.debug_peak = 0.0
        st.rerun()

st.warning(
    "This prototype sends recognized text through Supabase and plays a "
    "translated voice in the other participant's app. It does not replace "
    "or translate audio inside a normal SIM phone call. Browser autoplay "
    "may be blocked; press ▶ if the translated audio does not start."
)
