import base64
import html
import os
import time
import uuid
import wave

import numpy as np
import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from supabase import create_client

st.set_page_config(
    page_title="Anand Live Translator",
    page_icon="📞",
    layout="centered"
)

LANGUAGES = {
    "Telugu": "te-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "English": "en-IN",
}

DATA_DIR = "/tmp/anand_room_data"
os.makedirs(DATA_DIR, exist_ok=True)

required_secrets = (
    "SARVAM_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY"
)

missing = [
    key for key in required_secrets
    if not st.secrets.get(key)
]

if missing:
    st.error("Missing Streamlit Secrets: " + ", ".join(missing))
    st.stop()

sarvam = SarvamAI(
    api_subscription_key=st.secrets["SARVAM_API_KEY"]
)

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]}
    ]
})

DEFAULT_STATE = {
    "auth": False,
    "room": None,
    "my_id": str(uuid.uuid4())[:8],
    "my_listen": "Telugu",
    "buffer": [],
    "last_speech": 0.0,
    "is_speaking": False,
    "auto_lock": False,
    "call_start": 0.0,
    "last_message_id": 0,
    "played_audio": [],
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
        password = st.text_input(
            "App password",
            type="password"
        )

        submitted = st.form_submit_button(
            "Unlock",
            use_container_width=True
        )

    if submitted:
        if password == app_password:
            st.session_state.auth = True
            st.rerun()

        st.error("Incorrect password.")

    st.stop()

st.session_state.auth = True


def create_room_in_database(room_code):
    result = supabase.table("call_rooms").insert({
        "room_code": room_code,
        "created_by": st.session_state.my_id,
        "is_active": True,
    }).execute()

    return bool(result.data)


def room_exists(room_code):
    result = (
        supabase.table("call_rooms")
        .select("room_code,is_active")
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
    detected = getattr(response, "language_code", None)

    if not transcript and isinstance(response, dict):
        transcript = response.get("transcript", "")
        detected = response.get("language_code", detected)

    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError(
            f"Speech-to-text returned no transcript. Response: {response}"
        )

    return transcript.strip(), detected


def publish_message(text, source_language):
    result = supabase.table("call_messages").insert({
        "room_code": st.session_state.room,
        "sender_id": st.session_state.my_id,
        "original_text": text,
        "source_language": (
            source_language
            if source_language in LANGUAGES.values()
            else None
        ),
    }).execute()

    return result.data[0] if result.data else None


def process_buffer():
    if st.session_state.auto_lock:
        return

    if len(st.session_state.buffer) < 15:
        return

    st.session_state.auto_lock = True
    wav_path = None

    try:
        chunks = st.session_state.buffer[:]
        st.session_state.buffer = []
        st.session_state.is_speaking = False

        audio = np.concatenate(chunks).astype(np.int16)

        sample_rate = int(
            st.session_state.get("audio_sample_rate", 48000)
        )

        wav_path = os.path.join(
            DATA_DIR,
            f"{st.session_state.my_id}_{uuid.uuid4().hex}.wav"
        )

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())

        st.info(
            f"Audio captured: {len(audio) / sample_rate:.1f} seconds"
        )

        transcript, source_language = transcribe_audio(wav_path)

        publish_message(transcript, source_language)

        st.session_state.last_error = ""

        st.toast("Speech sent to call", icon="✅")

    except Exception as exc:
        st.session_state.last_error = (
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        st.session_state.auto_lock = False

        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


def translate_text(text, target_language, source_language=None):
    supported = set(LANGUAGES.values())

    source_code = (
        source_language
        if source_language in supported
        and source_language != target_language
        else "auto"
    )

    response = sarvam.text.translate(
        input=text,
        source_language_code=source_code,
        target_language_code=target_language,
        model="mayura:v1",
    )

    translated = getattr(
        response,
        "translated_text",
        None
    )

    if not translated and isinstance(response, dict):
        translated = response.get("translated_text")

    if not isinstance(translated, str) or not translated.strip():
        raise ValueError(
            f"Translation returned no text. Response: {response}"
        )

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
        raise ValueError(
            f"Text-to-speech returned no audio. Response: {response}"
        )

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(audios[0]))


def get_messages():
    result = (
        supabase.table("call_messages")
        .select(
            "id,room_code,sender_id,original_text,"
            "source_language,created_at"
        )
        .eq("room_code", st.session_state.room)
        .gt("id", st.session_state.last_message_id)
        .order("id")
        .limit(50)
        .execute()
    )

    return result.data or []
```
```python
st.markdown(
    """<div style="background:linear-gradient(135deg,#667eea,#764ba2);
    padding:22px;border-radius:18px;color:white;text-align:center">
    <h2>📞 Anand Live Translator</h2>
    <p>Speak your language. Understand theirs.</p>
    </div>""",
    unsafe_allow_html=True,
)

if not st.session_state.room:
    left, right = st.columns(2)

    with left:
        if st.button(
            "📞 Create Call",
            type="primary",
            use_container_width=True
        ):
            new_room_code = (
                "ANAND-" + uuid.uuid4().hex[:6].upper()
            )

            try:
                if create_room_in_database(new_room_code):
                    st.session_state.room = new_room_code
                    st.session_state.call_start = time.time()
                    st.session_state.last_message_id = 0
                    st.rerun()
                else:
                    st.error("Room create కాలేదు. మళ్లీ ప్రయత్నించండి.")

            except Exception as exc:
                st.error(
                    "Supabase room create failed: " + str(exc)
                )

    with right:
        with st.form("join_room"):
            room_code = st.text_input("Room code").strip().upper()

            if st.form_submit_button(
                "Join Call",
                use_container_width=True
            ):
                if not room_code:
                    st.warning("Enter a room code.")
                else:
                    try:
                        if room_exists(room_code):
                            st.session_state.room = room_code
                            st.session_state.call_start = time.time()
                            st.session_state.last_message_id = 0
                            st.session_state.played_audio = []
                            st.rerun()
                        else:
                            st.error(
                                "Invalid Room Code లేదా call close అయింది."
                            )

                    except Exception as exc:
                        st.error(
                            "Room validation failed: " + str(exc)
                        )

    st.info(
        "Share the room code with the other participant. "
        "Both participants must use the same deployed app."
    )

    st.stop()


elapsed = max(
    0,
    int(time.time() - st.session_state.call_start)
)

mins, secs = divmod(elapsed, 60)

st.markdown(
    f"**Room:** `{st.session_state.room}` · "
    f"**Call time:** {mins:02d}:{secs:02d}"
)

st.caption(
    f"Your participant ID: {st.session_state.my_id}"
)

st.session_state.my_listen = st.selectbox(
    "🌐 I want to hear in:",
    list(LANGUAGES.keys()),
    index=list(LANGUAGES.keys()).index(
        st.session_state.my_listen
    ),
)

target_code = LANGUAGES[st.session_state.my_listen]

st.caption(
    f"Incoming speech will be translated into "
    f"{st.session_state.my_listen}."
)

ctx = webrtc_streamer(
    key=f"mic-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={
        "video": False,
        "audio": True
    },
    audio_receiver_size=1024,
    async_processing=True,
)

if ctx and ctx.state.playing and ctx.audio_receiver:
    st.success("🎙️ Microphone connected")

    try:
        frames = ctx.audio_receiver.get_frames(timeout=0.2)

        for frame in frames:
            st.session_state.debug_audio_frames += 1

            frame_rate = getattr(frame, "sample_rate", None)

            if frame_rate:
                st.session_state.audio_sample_rate = int(frame_rate)

            arr = frame.to_ndarray()

            if arr.ndim == 2:
                pcm = arr.astype(np.float32).mean(axis=0)
            else:
                pcm = arr.astype(np.float32).flatten()

            if np.issubdtype(arr.dtype, np.floating):
                peak = (
                    float(np.max(np.abs(pcm)))
                    if pcm.size else 0.0
                )

                if peak <= 1.0:
                    pcm = pcm * 32767.0

            pcm = np.clip(
                pcm, -32768, 32767
            ).astype(np.int16)

            energy = (
                float(
                    np.sqrt(
                        np.mean(pcm.astype(np.float32) ** 2)
                    )
                )
                if pcm.size else 0.0
            )

            st.session_state.debug_peak = max(
                st.session_state.debug_peak,
                energy
            )

            if energy > 250:
                st.session_state.last_speech = time.time()
                st.session_state.is_speaking = True
                st.session_state.buffer.append(pcm)

            elif st.session_state.is_speaking:
                st.session_state.buffer.append(pcm)

    except Exception as exc:
        st.session_state.last_error = (
            f"Audio receiver: {type(exc).__name__}: {exc}"
        )


with st.expander("Audio diagnostics (for troubleshooting)"):
    st.write(
        f"Received audio frames: "
        f"{st.session_state.debug_audio_frames}"
    )

    st.write(
        f"Maximum audio level (RMS): "
        f"{st.session_state.debug_peak:.1f}"
    )

    st.write(
        f"Buffered audio chunks: "
        f"{len(st.session_state.buffer)}"
    )

    st.write(
        f"Speaking detected: "
        f"{st.session_state.is_speaking}"
    )

    if st.button("Reset audio diagnostics"):
        st.session_state.debug_audio_frames = 0
        st.session_state.debug_peak = 0.0
        st.rerun()


if (
    st.session_state.is_speaking
    and time.time() - st.session_state.last_speech > 1.2
):
    process_buffer()


if st.session_state.last_error:
    st.error(
        "Speech processing failed: "
        + st.session_state.last_error
    )


st.divider()
st.subheader("🌐 Incoming translated speech")


@st.fragment(run_every=2)
def incoming_messages():
    try:
        messages = get_messages()

    except Exception as exc:
        st.error(
            "Could not read messages from Supabase: "
            + str(exc)
        )
        return

    if not messages:
        st.caption(
            "Waiting for the other participant to speak..."
        )
        return

    for msg in messages:
        msg_id = int(msg["id"])

        st.session_state.last_message_id = max(
            st.session_state.last_message_id,
            msg_id
        )

        if msg.get("sender_id") == st.session_state.my_id:
            continue

        original = str(
            msg.get("original_text") or ""
        ).strip()

        if not original:
            continue

        st.markdown(
            '<div style="background:#20202b;color:white;'
            'padding:12px;border-radius:12px">'
            '<b>Original speech</b><br>'
            + html.escape(original)
            + '</div>',
            unsafe_allow_html=True,
        )

        try:
            translated = translate_text(
                original,
                target_code,
                msg.get("source_language")
            )

            audio_path = os.path.join(
                DATA_DIR,
                f"translated_{st.session_state.my_id}_"
                f"{msg_id}_{target_code}.wav"
            )

            if not os.path.exists(audio_path):
                generate_speech(
                    translated,
                    target_code,
                    audio_path
                )

            st.markdown(
                f"**Translation ({st.session_state.my_listen}):**"
            )

            st.write(translated)

            st.audio(
                audio_path,
                format="audio/wav",
                autoplay=False
            )

            st.info(
                "Translated voice vinadaniki audio player lo ▶ "
                "button click cheyyi."
            )

        except Exception as exc:
            st.error(
                "Translation/audio generation failed: "
                f"{type(exc).__name__}: {exc}"
            )


incoming_messages()


st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "🔄 Refresh",
        use_container_width=True
    ):
        st.rerun()

with col2:
    if st.button(
        "📞 End Call",
        type="primary",
        use_container_width=True
    ):
        try:
            supabase.table("call_rooms").update(
                {"is_active": False}
            ).eq(
                "room_code",
                st.session_state.room
            ).execute()

        except Exception as exc:
            st.warning(
                "Call ended on this device, but room status "
                "could not be updated: " + str(exc)
            )

        st.session_state.room = None
        st.session_state.buffer = []
        st.session_state.is_speaking = False
        st.session_state.call_start = 0.0
        st.session_state.last_message_id = 0
        st.session_state.played_audio = []
        st.session_state.debug_audio_frames = 0
        st.session_state.debug_peak = 0.0

        st.rerun()


st.warning(
    "Prototype note: this is chunked speech translation, "
    "not a raw live phone-call audio relay. "
    "After translation, press ▶ to play the generated audio. "
    "Use only test data until room-level database security is added."
)
