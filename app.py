from streamlit_webrtc import AudioProcessorBase
import av
import numpy as np

class HDVoiceProcessor(AudioProcessorBase):
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # No filter - raw HD audio pass through - real phone laaga
        return frame

# HD Quality - Real Phone Laaga
ctx = webrtc_streamer(
    key=f"hd-voice-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={
        "video": False,
        "audio": {
            "echoCancellation": False,      # OFF - real phone lo undadu
            "noiseSuppression": False,      # OFF - ide blur ki main villain
            "autoGainControl": False,       # OFF - natural voice
            "channelCount": 1,
            "sampleRate": {"ideal": 48000},
            "sampleSize": {"ideal": 16},
            "googEchoCancellation": False,
            "googAutoGainControl": False,
            "googNoiseSuppression": False,
            "googHighpassFilter": False,
            "googTypingNoiseDetection": False,
        }
    },
    audio_processor_factory=HDVoiceProcessor,  # HD pass-through
    audio_receiver_size=1024,
    audio_html_attrs={
        "autoPlay": True,
        "controls": True,  # volume control kosam
    },
    async_processing=True,
)
