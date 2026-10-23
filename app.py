import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os, time, uuid, base64, glob, wave
import numpy as np

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6].upper(),"my_listen":"Telugu","buffer":[],"last_speech":0,"is_speaking":False,"call_start":0,"auto_lock":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock Call",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data",exist_ok=True)

if not st.session_state.room:
    st.markdown("<div style='background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:24px;padding:28px;color:white;text-align:center'><h2>📞 Anand Translator</h2><p>Fixed - No Self Echo</p></div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call",use_container_width=True,type="primary"):
            new_room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=new_room
            st.session_state.call_start=time.time()
            open(f"room_data/{new_room}.room","w").write("room")
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join Call",use_container_width=True):
                rc=code.upper().strip().replace(" ","")
                if os.path.exists(f"room_data/{rc}.room") or os.path.exists(f"room_data/{rc}_users.txt"):
                    st.session_state.room=rc
                    st.session_state.call_start=time.time()
                    st.rerun()
                else:
                    st.error(f"❌ Room {rc} Not Found!")
    st.stop()

st.markdown("""
<style>
.block-container{max-width:400px!important}.stApp{background:#0a0a0f!important}
.call-header{background:#1c1c24;border-radius:24px;padding:18px;text-align:center;border:1px solid #222}
.timer{color:#10b981;font-weight:700}
.incoming-card{background:#1c1c24;border-radius:16px;padding:12px;margin:8px 0;border-left:4px solid #667eea}
.self-card{border-left:4px solid #555;background:#222}
</style>
""", unsafe_allow_html=True)

# Live count
now=time.time()
st.markdown(f"<div class='call-header'><h3 style='color:white;margin:0'>Room {st.session_state.room}</h3><p style='color:#888;margin:4px 0'>My ID: {st.session_state.my_id} • 👥 Live</p><div class='timer'>Auto Translate ON • No Self Play</div></div>", unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha (I Listen):", ["Telugu","Hindi","Tamil","English"])

ctx = webrtc_streamer(
    key=f"call-{st.session_state.room}-{st.session_state.my_id}",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    audio_receiver_size=1024,
    async_processing=True,
)

def process_buffer():
    if st.session_state.auto_lock or len(st.session_state.buffer) < 10:
        return
    st.session_state.auto_lock = True
    try:
        all_audio = np.concatenate(st.session_state.buffer)
        st.session_state.buffer = []
        st.session_state.is_speaking = False
        wav_path = f"room_data/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(48000)
            wf.writeframes(all_audio.astype(np.int16).tobytes())
        with open(wav_path,"rb") as f:
            try: stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
            except:
                f.seek(0)
                stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code="auto")
            orig = getattr(stt_res, 'transcript', '') or str(stt_res)
        if orig and len(orig.strip())>1:
            bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.txt"
            open(bfile,"w",encoding="utf-8").write(orig)
            st.toast(f"✅ Sent to others: {orig[:40]}")
    except Exception as e:
        st.error(f"STT Error: {e}")
    finally:
        st.session_state.auto_lock = False

if ctx and ctx.state.playing:
    st.success("🔴 LIVE - Matladu! 2 sec gap = Auto Sent to OTHER phone only")
    if ctx.audio_receiver:
        try:
            frames = ctx.audio_receiver.get_frames(timeout=0.4)
            for frame in frames:
                arr = frame.to_ndarray()
                pcm = arr.mean(axis=0) if arr.ndim==2 else arr.flatten()
                energy = np.sqrt(np.mean(pcm.astype(float)**2))
                if energy > 350:
                    st.session_state.last_speech = time.time()
                    st.session_state.is_speaking = True
                    st.session_state.buffer.append(pcm)
                elif st.session_state.is_speaking:
                    st.session_state.buffer.append(pcm)
        except: pass
    if st.session_state.is_speaking and (time.time() - st.session_state.last_speech) > 2.0:
        if len(st.session_state.buffer) > 15:
            with st.spinner("Sending to other phone..."):
                process_buffer()
            st.rerun()
else:
    st.warning("👇 START nokku - ne voice avathala phone ki mathrame velluthundi, neeke vinipinchadu")

st.divider()

@st.fragment(run_every=2)
def auto_incoming():
    st.markdown(f"### 🔊 Incoming - {st.session_state.my_listen} lo ONLY (Others voice)")
    
    all_files = sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
    
    # DEBUG - meeke telusthundi em files unnai ani
    st.caption(f"Debug: Room lo {len(all_files)} files | My ID: {st.session_state.my_id}")
    
    found_other=False
    for bfile in all_files[:10]:
        try:
            # FIXED: Exact sender ID extraction - self echo 100% poyindi
            basename = os.path.basename(bfile)
            sender_id = basename.split("_")[-1].replace(".txt","").strip().upper()
            my_id_clean = st.session_state.my_id.strip().upper()
            
            # Nee own file ayithe 100% skip - neeke vinipinchadu
            if sender_id == my_id_clean:
                continue
            
            if time.time()-os.path.getmtime(bfile)>300:
                continue
                
            orig_text=open(bfile,"r",encoding="utf-8").read().strip()
            if not orig_text or len(orig_text)<2:
                continue
                
            found_other=True
            tgt_code=lang_map[st.session_state.my_listen]
            mtime = int(os.path.getmtime(bfile))
            
            # Language tho cache - translate guarantee
            cache_audio=f"room_data/{st.session_state.room}_to_{my_id_clean}_from_{sender_id}_{mtime}_{st.session_state.my_listen}.wav"
            cache_txt=cache_audio.replace(".wav",".txt")
            
            if not os.path.exists(cache_audio):
                with st.spinner(f"Translating {sender_id} voice to {st.session_state.my_listen}..."):
                    trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                    translated = getattr(trans_res, 'translated_text', '') or orig_text
                    
                    open(cache_txt,"w",encoding="utf-8").write(f"{orig_text} ||| {translated}")
                    
                    # TTS with TRANSLATED text only
                    try:
                        tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anand", model="bulbul:v3")
                    except:
                        tts_res = client.text_to_speech.convert(text=translated, language_code=tgt_code, speaker="anand", model="bulbul:v3")
                    
                    ab64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                    if ab64:
                        try: data=base64.b64decode(ab64)
                        except: data=ab64.encode() if isinstance(ab64,str) else ab64
                        open(cache_audio,"wb").write(data)
            
            if os.path.exists(cache_audio):
                txt_data = open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig_text
                if "|||" in txt_data:
                    orig_part, trans_part = txt_data.split("|||")
                else:
                    orig_part, trans_part = orig_text, txt_data
                
                st.markdown(f"<div class='incoming-card'>👤 <b>{sender_id} (Original):</b> {orig_part}<br>🔊 <b>Translated to {st.session_state.my_listen}:</b> {trans_part}</div>", unsafe_allow_html=True)
                st.audio(cache_audio, autoplay=True)
                
        except Exception as e:
            st.error(f"Error with {bfile}: {e}")
    
    if not found_other:
        st.info(f"Waiting for OTHER phone voice in {st.session_state.room}... Nee voice neeke raadu, avathala phone matladithe ne vasthundi")

auto_incoming()

if st.button("🗑️ Clear Room (Test fresh)"):
    for f in glob.glob(f"room_data/{st.session_state.room}_*"):
        try: os.remove(f)
        except: pass
    st.success("Cleared - malla test chey")
    st.rerun()
