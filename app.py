import streamlit as st
from sarvamai import SarvamAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os, time, uuid, base64, glob, wave, json
import numpy as np

try: API_KEY = st.secrets["SARVAM_API_KEY"]
except: st.error("🔑 API Key missing"); st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
st.set_page_config(page_title="Anand Translator", layout="centered")

for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_speak":"Hindi","my_listen":"Telugu","buffer":[],"last_speech":0,"is_speaking":False,"call_start":0,"auto_lock":False}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<div style='text-align:center;padding:40px'><h1>🔒</h1></div>", unsafe_allow_html=True)
    with st.form("login_form"):
        pwd=st.text_input("Password",type="password")
        if st.form_submit_button("Unlock Call",use_container_width=True,type="primary") and pwd=="meAbu":
            st.session_state.auth=True; st.rerun()
    st.stop()

os.makedirs("room_data",exist_ok=True)

if not st.session_state.room:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:24px;padding:28px;color:white;text-align:center'>
    <h2>📞 Anand Translator</h2><p>Real Call UI - Option A</p></div>
    """, unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call",use_container_width=True,type="primary"):
            new_room=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=new_room
            st.session_state.call_start=time.time()
            open(f"room_data/{new_room}.room","w").write("room")
            open(f"room_data/{new_room}_users.txt","w").write(f"{st.session_state.my_id}|{time.time()}\n")
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

# CSS same
st.markdown("""
<style>
.block-container{max-width:400px!important;padding-top:1rem!important}
.stApp{background:#0a0a0f!important}
.call-header{background:linear-gradient(180deg,#1c1c24 0%,#0a0a0f 100%);border-radius:24px;padding:20px;text-align:center;border:1px solid #222}
.avatar{width:80px;height:80px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:36px}
.timer{color:#10b981;font-weight:700;font-size:14px;margin-top:8px}
.live-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;animation:blink 1s infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0.3}100%{opacity:1}}
.pulse-ring{animation:pulse 1.8s infinite}
@keyframes pulse{0%{transform:scale(0.95);box-shadow:0 0 0 0 rgba(102,126,234,0.7)}70%{transform:scale(1);box-shadow:0 0 0 20px rgba(102,126,234,0)}100%{transform:scale(0.95);box-shadow:0 0 0 0 rgba(102,126,234,0)}}
.incoming-card{background:#1c1c24;border-radius:16px;padding:14px;margin:10px 0;border-left:4px solid #667eea}
.speaking{background:linear-gradient(90deg,#667eea22,#764ba222);border:1px solid #667eea55}
.control-label{color:#888!important;font-size:11px!important;text-align:center!important;margin-top:6px!important}
</style>
""", unsafe_allow_html=True)

cf=f"room_data/{st.session_state.room}_users.txt"
now=time.time()
users={}
if os.path.exists(cf):
    with open(cf,"r") as f:
        for l in f:
            if "|" in l:
                try:
                    uid,t=l.strip().split("|")
                    if now-float(t)<60: users[uid]=float(t)
                except: pass
users[st.session_state.my_id]=now
with open(cf,"w") as f:
    for uid,t in users.items(): f.write(f"{uid}|{t}\n")

call_duration = int(now - st.session_state.call_start) if st.session_state.call_start else 0
mins, secs = divmod(call_duration, 60)

st.markdown(f"""
<div class='call-header'>
<div class='avatar'>👤</div>
<h3 style='color:white;margin:12px 0 4px 0'>Room {st.session_state.room}</h3>
<p style='color:#888;margin:0'>ID: {st.session_state.my_id} • 👥 {len(users)} online</p>
<div class='timer'><span class='live-dot'></span> {mins:02d}:{secs:02d} • Auto Listening ON</div>
</div>
""", unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

# FIX 1: Rendu selectboxes - Nuvvu em matladutunnav, em vintunnav
c1,c2 = st.columns(2)
with c1: st.session_state.my_speak=st.selectbox("I Speak:", ["Hindi","Telugu","Tamil","English"], index=0)
with c2: st.session_state.my_listen=st.selectbox("I Listen:", ["Telugu","Hindi","Tamil","English"], index=1)

st.markdown("###")
ctx = webrtc_streamer(
    key=f"call-{st.session_state.room}",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video":False,"audio":True},
    audio_receiver_size=4096, # FIX 2: 1024 -> 4096 queue overflow fix
    async_processing=True,
)

def process_buffer():
    if st.session_state.auto_lock or len(st.session_state.buffer) < 15:
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
            # FIX 3: Nee speak language tho STT - Hindi matladithe Hindi ga detect
            stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3", language_code=lang_map[st.session_state.my_speak])
            orig = getattr(stt_res, 'transcript', '') or str(stt_res)
        if orig and len(orig.strip())>1:
            # FIX 4: JSON lo text + language kalipi save - ide main fix
            bfile=f"room_data/{st.session_state.room}_broadcast_{int(time.time())}_{st.session_state.my_id}.json"
            payload={"text":orig,"lang":lang_map[st.session_state.my_speak],"lang_name":st.session_state.my_speak}
            open(bfile,"w",encoding="utf-8").write(json.dumps(payload, ensure_ascii=False))
            st.toast(f"✅ Sent: {orig[:40]}")
    except Exception as e:
        st.error(f"{e}")
    finally:
        st.session_state.auto_lock = False

col_mic1, col_mic2, col_mic3 = st.columns([1,1,1])
with col_mic2:
    if ctx and ctx.state.playing:
        st.markdown("<div class='pulse-ring' style='text-align:center'><div style='width:72px;height:72px;background:#10b981;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:32px'>🎙️</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='control-label' style='color:#10b981!important'>🔴 LISTENING<br>2 sec gap = Auto Sent</div>", unsafe_allow_html=True)
        if ctx.audio_receiver:
            try:
                frames = ctx.audio_receiver.get_frames(timeout=0.4)
                for frame in frames:
                    arr = frame.to_ndarray()
                    pcm = arr.mean(axis=0) if arr.ndim==2 else arr.flatten()
                    energy = np.sqrt(np.mean(pcm.astype(float)**2))
                    if energy > 400:
                        st.session_state.last_speech = time.time()
                        if not st.session_state.is_speaking:
                            st.session_state.is_speaking = True
                        st.session_state.buffer.append(pcm)
                    elif st.session_state.is_speaking:
                        st.session_state.buffer.append(pcm)
            except: pass
        if st.session_state.is_speaking and (time.time() - st.session_state.last_speech) > 2.0:
            if len(st.session_state.buffer) > 20:
                with st.spinner("Sending..."):
                    process_buffer()
                st.success("✅ Sent! Continue speaking...")
                time.sleep(0.3)
                st.rerun()
    else:
        st.markdown("<div style='text-align:center'><div style='width:72px;height:72px;background:#2a2a35;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:28px'>🎙️</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='control-label'>Tap START above to talk</div>", unsafe_allow_html=True)

c1,c2,c3,c4 = st.columns(4)
with c1:
    if st.button("🔇", key="mute"): st.toast("Mute")
    st.markdown("<div class='control-label'>Mute</div>", unsafe_allow_html=True)
with c2:
    if st.button("🔊", key="spk"): st.toast("Speaker")
    st.markdown("<div class='control-label'>Speaker</div>", unsafe_allow_html=True)
with c3:
    if st.button("📝", key="notes"): st.info(f"Room: {st.session_state.room}")
    st.markdown("<div class='control-label'>Notes</div>", unsafe_allow_html=True)
with c4:
    if st.button("📞", key="end"):
        st.session_state.room=None
        st.rerun()
    st.markdown("<div class='control-label' style='color:#ef4444!important'>End</div>", unsafe_allow_html=True)

st.divider()

@st.fragment(run_every=1.5)
def auto_incoming():
    broadcasts=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.json"), reverse=True)
    old_txt=sorted(glob.glob(f"room_data/{st.session_state.room}_broadcast_*.txt"), reverse=True)
    all_files = broadcasts + old_txt
    
    recent_other = None
    for b in all_files:
        if st.session_state.my_id not in b and time.time()-os.path.getmtime(b) < 3:
            recent_other = b
            break
    if recent_other:
        st.markdown(f"<div class='incoming-card speaking'>🗣️ Other person speaking... <span style='float:right'>•••</span></div>", unsafe_allow_html=True)
    
    st.markdown(f"**Incoming - {st.session_state.my_listen}**")
    found=False
    for bfile in all_files[:5]:
        try:
            if st.session_state.my_id in bfile: continue
            if time.time()-os.path.getmtime(bfile)>300: continue
            
            # FIX 5: JSON chaduvutundi - language tho
            raw=open(bfile,"r",encoding="utf-8").read()
            try:
                j=json.loads(raw)
                orig_text=j["text"]; src_lang=j["lang"]; src_name=j["lang_name"]
            except:
                orig_text=raw; src_lang="hi-IN"; src_name="Hindi"
            
            if not orig_text: continue
            found=True
            tgt_code=lang_map[st.session_state.my_listen]
            
            # PERFECT TRANSLATION: src_lang -> tgt_code
            cache_audio=f"room_data/{st.session_state.room}_to_{st.session_state.my_id}_from_{src_name}_{int(os.path.getmtime(bfile))}_{st.session_state.my_listen}.wav"
            cache_txt=cache_audio.replace(".wav",".txt")
            
            if not os.path.exists(cache_audio):
                if src_lang == tgt_code:
                    translated = orig_text
                else:
                    trans_res = client.text.translate(input=orig_text, source_language_code=src_lang, target_language_code=tgt_code, model="mayura:v1")
                    translated = getattr(trans_res, 'translated_text', orig_text)
                open(cache_txt,"w",encoding="utf-8").write(f"{src_name}: {orig_text} -> {st.session_state.my_listen}: {translated}")
                try: tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, speaker="anand", model="bulbul:v3")
                except: tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, model="bulbul:v3")
                ab64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                if ab64:
                    try: data=base64.b64decode(ab64)
                    except: data=ab64.encode() if isinstance(ab64,str) else ab64
                    open(cache_audio,"wb").write(data)
            
            if os.path.exists(cache_audio):
                info=open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig_text
                st.markdown(f"<div class='incoming-card'>👤 <b>{src_name}:</b> {info}</div>", unsafe_allow_html=True)
                st.audio(cache_audio, autoplay=True)
        except Exception as e:
            st.error(f"{e}")
    if not found:
        st.caption(f"Waiting in {st.session_state.room}... Same code tho join ayithe auto vastundi")

auto_incoming()
