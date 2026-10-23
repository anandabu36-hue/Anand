import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import (
    webrtc_streamer,
    WebRtcMode,
    RTCConfiguration,
)
import os
import time
import uuid
import base64
import glob
import wave
import json
import threading
import numpy as np

# =========================================================
# 1. CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Anand Live Translator",
    page_icon="📞",
    layout="centered",
)

try:
    API_KEY = st.secrets["SARVAM_API_KEY"]
except Exception:
    st.error(
        "SARVAM_API_KEY missing. "
        "Add your API key to Streamlit secrets."
    )
    st.stop()

client = SarvamAI(api_subscription_key=API_KEY)

DATA_DIR = "room_data"
os.makedirs(DATA_DIR, exist_ok=True)

RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]}
    ]
})

LANGUAGES = {
    "Telugu": "te-IN",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "English": "en-IN",
}

DEFAULT_STATE = {
    "auth": False,
    "room": None,
    "my_id": str(uuid.uuid4())[:6],
    "my_listen": "Telugu",
    "buffer": [],
    "last_speech": 0.0,
    "is_speaking": False,
    "auto_lock": False,
    "call_start": 0.0,
    "played_audio": [],
    "last_error": "",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 2. LOGIN
# =========================================================

if not st.session_state.auth:

    st.title("🔒 Anand Live Translator")
    st.caption("Secure prototype access")

    with st.form("login_form"):
        password = st.text_input(
            "Password",
            type="password",
        )

        submitted = st.form_submit_button(
            "Unlock Call",
            use_container_width=True,
        )

        if submitted:
            if password == "meAbu":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    st.stop()


# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

def safe_filename(value):
    """Remove unsafe filename characters."""
    return "".join(
        c for c in value
        if c.isalnum() or c in "-_"
    )


def room_users_file():
    return os.path.join(
        DATA_DIR,
        f"{st.session_state.room}_users.json",
    )


def broadcast_pattern():
    return os.path.join(
        DATA_DIR,
        f"{st.session_state.room}_broadcast_*.json",
    )


def save_broadcast(text, source_language):
    """
    Publish recognized speech to the shared room.

    This requires both participants to use the same
    server-side storage.
    """
    room = st.session_state.room
    user_id = st.session_state.my_id

    message_id = (
        f"{int(time.time() * 1000)}_"
        f"{user_id}_"
        f"{uuid.uuid4().hex[:6]}"
    )

    filename = os.path.join(
        DATA_DIR,
        f"{room}_broadcast_{message_id}.json",
    )

    payload = {
        "message_id": message_id,
        "sender": user_id,
        "text": text,
        "source_language": source_language,
        "created_at": time.time(),
    }

    temp_file = filename + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    os.replace(temp_file, filename)

    return filename


def transcribe_audio(wav_path):
    """
    Convert recorded speech into text.
    Saaras returns the transcript and detected language.
    """
    with open(wav_path, "rb") as audio_file:
        response = client.speech_to_text.transcribe(
            file=audio_file,
            model="saaras:v3",
            mode="transcribe",
        )

    transcript = getattr(response, "transcript", "")
    detected_language = getattr(
        response,
        "language_code",
        None,
    )

    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError(
            "Speech recognition returned empty text."
        )

    return transcript.strip(), detected_language


def process_buffer():
    """
    Record buffered audio, transcribe it, and publish
    the original transcript for the other participant.
    """
    if st.session_state.auto_lock:
        return

    if len(st.session_state.buffer) < 15:
        return

    st.session_state.auto_lock = True

    try:
        audio_chunks = st.session_state.buffer[:]
        st.session_state.buffer = []
        st.session_state.is_speaking = False

        audio = np.concatenate(audio_chunks).astype(np.int16)

        wav_path = os.path.join(
            DATA_DIR,
            (
                f"{st.session_state.room}_"
                f"{st.session_state.my_id}_"
                f"{uuid.uuid4().hex}.wav"
            ),
        )

        # The WebRTC audio is expected to be 48 kHz.
        # Confirm the actual incoming frame sample rate
        # if your deployment uses a different configuration.
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(audio.tobytes())

        transcript, source_language = transcribe_audio(
            wav_path
        )

        # Publish original transcript, not the translated
        # transcript. Each receiver chooses its own language.
        save_broadcast(
            transcript,
            source_language,
        )

        st.session_state.last_error = ""

    except Exception as exc:
        st.session_state.last_error = str(exc)

    finally:
        st.session_state.auto_lock = False


def translate_text(text, target_language):
    """
    Translate recognized speech into the receiver's language.
    """
    response = client.text.translate(
        input=text,
        source_language_code="auto",
        target_language_code=target_language,
        model="mayura:v1",
    )

    translated = getattr(
        response,
        "translated_text",
        None,
    )

    if not isinstance(translated, str) or not translated.strip():
        raise ValueError(
            "Translation API returned empty text."
        )

    return translated.strip()


def generate_speech(text, target_language, output_path):
    """
    Generate a WAV voice recording from translated text.
    """
    response = client.text_to_speech.convert(
        text=text,
        language_code=target_language,
        speaker="anand",
        model="bulbul:v3",
        output_audio_codec="wav",
    )

    audios = getattr(response, "audios", None)

    if not audios or not audios[0]:
        raise ValueError(
            "Text-to-Speech API returned no audio."
        )

    audio_bytes = base64.b64decode(audios[0])

    with open(output_path, "wb") as f:
        f.write(audio_bytes)


def translate_and_generate(payload, target_language):
    """
    Cache translation text and generated voice for a message.
    """
    room = safe_filename(st.session_state.room)
    message_id = safe_filename(payload["message_id"])

    cache_base = os.path.join(
        DATA_DIR,
        f"{room}_{message_id}_{target_language}",
    )

    text_path = cache_base + ".txt"
    audio_path = cache_base + ".wav"

    if os.path.exists(text_path) and os.path.exists(audio_path):
        with open(text_path, "r", encoding="utf-8") as f:
            translated = f.read()

        return translated, audio_path

    translated = translate_text(
        payload["text"],
        target_language,
    )

    # Generate audio before marking the translation complete.
    generate_speech(
        translated,
        target_language,
        audio_path,
    )

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(translated)

    return translated, audio_path


# =========================================================
# 4. CREATE OR JOIN CALL
# =========================================================

if not st.session_state.room:

    st.markdown(
        """
        <div style="
            background:linear-gradient(135deg,#667eea,#764ba2);
            padding:24px;
            border-radius:20px;
            color:white;
            text-align:center;">
            <h2>📞 Anand Live Translator</h2>
            <p>Speak your language. Understand theirs.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📞 Create Call",
            use_container_width=True,
            type="primary",
        ):
            room = (
                "ANAND-"
                + uuid.uuid4().hex[:6].upper()
            )

            st.session_state.room = room
            st.session_state.call_start = time.time()

            room_path = os.path.join(
                DATA_DIR,
                f"{room}.room",
            )

            with open(room_path, "w") as f:
                f.write("room")

            st.rerun()

    with col2:
        with st.form("join_form"):
            room_code = st.text_input("Room Code")

            if st.form_submit_button(
                "Join Call",
                use_container_width=True,
            ):
                room_code = room_code.strip().upper()

                room_path = os.path.join(
                    DATA_DIR,
                    f"{room_code}.room",
                )

                if os.path.exists(room_path):
                    st.session_state.room = room_code
                    st.session_state.call_start = time.time()
                    st.rerun()
                else:
                    st.error(
                        "Room not found. Check the room code."
                    )

    st.info(
        "Both participants must connect to the same "
        "deployed application and shared room storage."
    )

    st.stop()


# =========================================================
# 5. CALL UI
# =========================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 480px;
        padding-top: 1rem;
    }

    .call-header {
        background: #171720;
        border-radius: 22px;
        padding: 24px;
        color: white;
        text-align: center;
        border: 1px solid #303040;
    }

    .avatar {
        width: 78px;
        height: 78px;
        border-radius: 50%;
        margin: auto;
        background: linear-gradient(135deg,#667eea,#764ba2);
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 35px;
    }

    .incoming-card {
        background: #20202b;
        padding: 14px;
        border-radius: 12px;
        margin: 10px 0;
        overflow-wrap: anywhere;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

elapsed = max(
    0,
    int(time.time() - st.session_state.call_start),
)

minutes, seconds = divmod(elapsed, 60)

st.markdown(
    f"""
    <div class="call-header">
        <div class="avatar">👤</div>
        <h3>Room {st.session_state.room}</h3>
        <p>📞 {minutes:02d}:{seconds:02d}</p>
        <p>Live Translation Prototype</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

st.session_state.my_listen = st.selectbox(
    "🌐 I want to hear in:",
    list(LANGUAGES.keys()),
    index=list(LANGUAGES.keys()).index(
        st.session_state.my_listen
    ),
)

target_language = LANGUAGES[
    st.session_state.my_listen
]

st.caption(
    f"Incoming speech will be translated into "
    f"{st.session_state.my_listen}."
)


# =========================================================
# 6. MICROPHONE / AUDIO RECEIVER
# =========================================================

ctx = webrtc_streamer(
    key=f"call-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={
        "video": False,
        "audio": True,
    },
    audio_receiver_size=1024,
    async_processing=True,
)

if ctx and ctx.state.playing:

    st.success("🎙️ Microphone connected")

    if ctx.audio_receiver:

        try:
            frames = ctx.audio_receiver.get_frames(
                timeout=0.2
            )

            for frame in frames:

                arr = frame.to_ndarray()

                # Convert multichannel audio to mono.
                if arr.ndim == 2:
                    if arr.shape[0] <= 2:
                        pcm = arr.mean(axis=0)
                    else:
                        pcm = arr.mean(axis=1)
                else:
                    pcm = arr.flatten()

                # Convert normalized float audio to int16 PCM.
                if np.issubdtype(
                    pcm.dtype,
                    np.floating,
                ):
                    pcm = np.clip(
                        pcm,
                        -1.0,
                        1.0,
                    )

                    pcm = (
                        pcm * 32767
                    ).astype(np.int16)

                else:
                    pcm = np.clip(
                        pcm,
                        -32768,
                        32767,
                    ).astype(np.int16)

                energy = float(
                    np.sqrt(
                        np.mean(
                            pcm.astype(np.float32) ** 2
                        )
                    )
                )

                if energy > 400:

                    st.session_state.last_speech = time.time()
                    st.session_state.is_speaking = True
                    st.session_state.buffer.append(pcm)

                elif st.session_state.is_speaking:

                    # Keep trailing silence so the last words
                    # are not cut off.
                    st.session_state.buffer.append(pcm)

        except Exception:
            # A timeout can occur when no new audio frames arrive.
            pass

    # Stop a speech segment after 2 seconds of silence.
    if (
        st.session_state.is_speaking
        and time.time() - st.session_state.last_speech > 2.0
    ):
        process_buffer()

    if st.session_state.last_error:
        st.error(
            "Speech processing failed: "
            + st.session_state.last_error
        )

else:
    st.info(
        "Start the microphone above, then speak normally."
    )


# =========================================================
# 7. CALL CONTROLS
# =========================================================

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "🔄 Refresh",
        use_container_width=True,
    ):
        st.rerun()

with col2:
    if st.button(
        "📞 End Call",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.room = None
        st.session_state.buffer = []
        st.session_state.is_speaking = False
        st.session_state.call_start = 0.0
        st.rerun()


# =========================================================
# 8. INCOMING SPEECH TRANSLATION
# =========================================================

st.divider()
st.subheader("🌐 Incoming Translated Speech")


@st.fragment(run_every=2)
def auto_incoming():

    my_id = st.session_state.my_id
    target_code = LANGUAGES[
        st.session_state.my_listen
    ]

    broadcasts = sorted(
        glob.glob(broadcast_pattern()),
        key=os.path.getmtime,
        reverse=True,
    )

    other_messages = []

    for broadcast in broadcasts:

        try:
            with open(
                broadcast,
                "r",
                encoding="utf-8",
            ) as f:
                payload = json.load(f)

            if payload.get("sender") == my_id:
                continue

            if not payload.get("text", "").strip():
                continue

            # Do not process old messages indefinitely.
            if (
                time.time()
                - float(payload.get("created_at", 0))
                > 300
            ):
                continue

            other_messages.append(
                (broadcast, payload)
            )

        except Exception:
            continue

    if not other_messages:
        st.caption(
            "Waiting for the other participant to speak..."
        )
        return

    # Display a limited number of recent messages.
    for broadcast, payload in reversed(
        other_messages[:5]
    ):

        st.markdown(
            f"""
            <div class="incoming-card">
                <b>👤 {payload.get("sender", "Caller")}</b>
                <br>
                <small>Original speech</small>
                <br>
                {payload["text"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:

            translated, audio_path = translate_and_generate(
                payload,
                target_code,
            )
            st.write("Original speech:", payload["text"])
            st.write("Selected language:", st.session_state.my_listen)
            st.write("Target language code:", target_code)
            st.write("Translated text:", translated)
            st.write("Generated audio:", audio_path)

            st.markdown(
                f"**Translation ({st.session_state.my_listen}):**"
            )

            st.write(translated)

            message_id = payload["message_id"]

            # Autoplay a message only once per browser session.
            already_played = (
                message_id
                in st.session_state.played_audio
            )

            st.audio(
                audio_path,
                format="audio/wav",
                autoplay=not already_played,
            )

            if not already_played:
                st.session_state.played_audio.append(
                    message_id
                )

        except Exception as exc:

            st.error(
                "Translation/audio generation failed: "
                + str(exc)
            )


auto_incoming()
