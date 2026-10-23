import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os, time, uuid, base64, wave
import numpy as np
from supabase import create_client

try:
    API_KEY = st.secrets["SARVAM_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("🔑 Secrets missing - SARVAM_API_KEY, SUPABASE_URL, SUPABASE_KEY add chey")
    st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6].upper(),"my_listen":"Telugu","buffer":[],"last_speech":0,"is_speaking":False,"call_start":0,"auto_lock":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

if not st.session_state.room:
    st.markdown("<div style='background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:24px;padding:28px;color:white;text-align:center'><h2>📞 Anand Translator</h2><p>Supabase - Voice 100% Reach + Translate</p></div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call",use_container_width=True,type="primary"):
            new_room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=new_room
            st.session_state.call_start=time.time()
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code")
            if st.form_submit_button("Join Call",use_container_width=True):
                st.session_state.room=code.upper().strip().replace(" ","")
                st.session_state.call_start=time.time()
                st.rerun()
    st.stop()

st.markdown("""
<style>
.block-container{max-width:400px!important}.stApp{background:#0a0a0f!important}
.call-header{background:#1c1c24;border-radius:24px;padding:18px;text-align:center;border:1px solid #222}
.timer{color:#10b981;font-weight:700}
.incoming-card{background:#1c1c24;border-radius:16px;padding:12px;margin:8px 0;border-left:4px solid #10b981}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<div class='call-header'><h3 style='color:white;margin:0'>Room {st.session_state.room}</h3><p style='color:#888'>My ID: {st.session_state.my_id} • Supabase Live</p><div class='timer'>Translate to {st.session_state.my_listen} • Auto Reach</div></div>", unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha:", ["Telugu","Hindi","Tamil","English"])

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
        wav_path = f"/tmp/{st.session_state.room}_{st.session_state.my_id}_in_{int(time.time())}.wav"
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
            # FIXED: Supabase lo save - 100% reach avuthundi
            supabase.table("broadcasts").insert({
                "room_code": st.session_state.room,
                "sender_id": st.session_state.my_id,
                "original_text": orig
            }).execute()
            st.toast(f"✅ Sent to Supabase: {orig[:40]} -> Will be translated to others language")
    except Exception as e:
        st.error(f"STT/Supabase Error: {e}")
    finally:
        st.session_state.auto_lock = False

if ctx and ctx.state.playing:
    st.success("🔴 LIVE - Matladu! 2 sec gap = Auto Sent to Supabase -> Other phone ki translate ayyi velluthundi")
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
            with st.spinner("Sending to other phone via Supabase..."):
                process_buffer()
            st.rerun()
else:
    st.warning("👇 START nokku - okkasari nokkithe chalu")

st.divider()

@st.fragment(run_every=2)
def auto_incoming():
    st.markdown(f"### 🔊 Incoming - {st.session_state.my_listen} lo (Supabase Live)")
    try:
        # Supabase nundi vere vallavi matrame teesuko - self skip
        res = supabase.table("broadcasts").select("*").eq("room_code", st.session_state.room).neq("sender_id", st.session_state.my_id).order("created_at", desc=True).limit(5).execute()
        rows = res.data if res.data else []
        
        if not rows:
            st.info(f"Waiting for other phone in {st.session_state.room}... Same code tho join ayi matladandi")
            return
        
        for row in rows:
            try:
                orig_text = row["original_text"]
                sender_id = row["sender_id"]
                created_at = row["created_at"]
                tgt_code = lang_map[st.session_state.my_listen]
                
                # Cache with supabase id + language
                cache_audio = f"/tmp/{st.session_state.room}_to_{st.session_state.my_id}_from_{sender_id}_{row['id']}_{st.session_state.my_listen}.wav"
                cache_txt = cache_audio.replace(".wav",".txt")
                
                if not os.path.exists(cache_audio):
                    trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                    translated = getattr(trans_res, 'translated_text', '') or orig_text
                    
                    open(cache_txt,"w",encoding="utf-8").write(f"{orig_text}|||{translated}")
                    
                    try: tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anand", model="bulbul:v3")
                    except: tts_res = client.text_to_speech.convert(text=translated, language_code=tgt_code, speaker="anand", model="bulbul:v3")
                    
                    ab64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                    if ab64:
                        try: data=base64.b64decode(ab64)
                        except: data=ab64.encode() if isinstance(ab64,str) else ab64
                        open(cache_audio,"wb").write(data)
                
                if os.path.exists(cache_audio):
                    txt_data = open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else f"{orig_text}|||{orig_text}"
                    o,t = txt_data.split("|||",1) if "|||" in txt_data else (orig_text, txt_data)
                    st.markdown(f"<div class='incoming-card'><div style='color:#888;font-size:11px'>👤 {sender_id}: {o}</div><div style='color:#fff;font-weight:600'>🔊 Translated to {st.session_state.my_listen}: {t}</div></div>", unsafe_allow_html=True)
                    st.audio(cache_audio, autoplay=True)
            except Exception as e:
                st.error(f"Translate Error: {e}")
    except Exception as e:
        st.error(f"Supabase Error: {e}")

auto_incoming()

if st.button("🗑️ Clear Room Messages"):
    supabase.table("broadcasts").delete().eq("room_code", st.session_state.room).execute()
    st.success("Cleared")
    st.rerun()
