import streamlit as st
from sarvamai import SarvamAI
from supabase import create_client
import os, time, uuid, base64, glob

# --- SECRETS ---
try:
    API_KEY = st.secrets["SARVAM_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("🔑 Secrets missing - Add SARVAM_API_KEY, SUPABASE_URL, SUPABASE_KEY in Streamlit Cloud")
    st.stop()

client = SarvamAI(api_subscription_key=API_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

st.set_page_config(page_title="Anand Translator", layout="centered", initial_sidebar_state="collapsed")

# --- SESSION ---
for k,v in {"auth":False,"room":None,"my_id":str(uuid.uuid4())[:6],"my_listen":"Telugu","call_start":0}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.auth:
    st.markdown("<div style='text-align:center;padding:60px'><h1>🔒</h1><h3>Anand Translator</h3></div>", unsafe_allow_html=True)
    with st.form("login"):
        pwd=st.text_input("Password", type="password")
        if st.form_submit_button("Unlock Call", use_container_width=True, type="primary") and pwd=="meAbu":
            st.session_state.auth=True
            st.rerun()
    st.stop()

os.makedirs("room_data", exist_ok=True)

# --- ROOM SELECTION ---
if not st.session_state.room:
    st.markdown("<h2 style='text-align:center'>📞 Anand Translator</h2>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📞 Create Call", use_container_width=True, type="primary"):
            new_code=f"ANAND-{str(uuid.uuid4())[:5].upper()}"
            st.session_state.room=new_code
            st.session_state.call_start=time.time()
            # Create room marker in Supabase - so others can find it
            try:
                supabase.table("broadcasts").insert({
                    "room_id": new_code,
                    "sender_id": "SYSTEM",
                    "text": f"Room {new_code} created",
                    "src_lang": "en-IN",
                    "src_name": "System"
                }).execute()
            except: pass
            st.rerun()
    with c2:
        with st.form("join_form"):
            code=st.text_input("Room Code (ANAND-XXXXX)")
            submitted=st.form_submit_button("Join Call", use_container_width=True)
            if submitted:
                rc=code.upper().strip().replace(" ","")
                # Validation: ANAND- format lo undala
                if not rc.startswith("ANAND-") or len(rc)<9:
                    st.error("❌ Invalid code! Format: ANAND-XXXXX")
                else:
                    # Check if room exists in Supabase
                    try:
                        res=supabase.table("broadcasts").select("room_id").eq("room_id", rc).limit(1).execute()
                        if not res.data:
                            st.error(f"❌ Room {rc} Not Found! Create chesi malli try chey")
                        else:
                            st.session_state.room=rc
                            st.session_state.call_start=time.time()
                            st.rerun()
                    except Exception as e:
                        # If Supabase error, allow but warn
                        st.session_state.room=rc
                        st.session_state.call_start=time.time()
                        st.rerun()
    st.stop()

# --- REAL PHONE UI CSS ---
st.markdown("""
<style>
.block-container{max-width:420px!important;padding-top:1rem!important}
.stApp{background:#0a0a0f!important}
.call-header{background:linear-gradient(180deg,#1c1c24 0%,#111115 100%);border-radius:24px;padding:20px;text-align:center;border:1px solid #222}
.avatar{width:72px;height:72px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:32px;color:white}
.timer{color:#10b981;font-weight:700;font-size:13px;margin-top:8px}
.live-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;animation:blink 1s infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0.3}100%{opacity:1}}
.lang-btn{background:linear-gradient(135deg,#10b981 0%,#059669 100%)!important;border-radius:50%!important;width:88px!important;height:88px!important;box-shadow:0 0 30px rgba(16,185,129,0.5)}
.control-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin:16px 0}
.control-item{text-align:center}
.control-icon{width:56px;height:56px;background:#1f2937;border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto;font-size:22px}
.control-label{color:#9ca3af;font-size:11px;margin-top:6px}
.translate-banner{background:linear-gradient(90deg,#10b98122,#667eea22);border:1px solid #10b98144;border-radius:12px;padding:10px;text-align:center;color:#10b981;font-weight:600;font-size:13px;margin:12px 0}
.incoming-card{background:#1c1c24;border-radius:16px;padding:14px;margin:10px 0;border-left:4px solid #10b981}
</style>
""", unsafe_allow_html=True)

lang_map={"Hindi":"hi-IN","Telugu":"te-IN","Tamil":"ta-IN","English":"en-IN"}

# Call Header
dur=int(time.time()-st.session_state.call_start) if st.session_state.call_start else 0
m,s=divmod(dur,60)
users_count=1 # Supabase lo count cheyadam kastam, simple

st.markdown(f"""
<div class='call-header'>
<div class='avatar'>👤</div>
<h3 style='color:white;margin:10px 0 4px 0'>{st.session_state.room}</h3>
<p style='color:#888;margin:0'>ID: {st.session_state.my_id} • Live</p>
<div class='timer'><span class='live-dot'></span> {m:02d}:{s:02d} • Secured</div>
</div>
""", unsafe_allow_html=True)

# Language Selection - The MAIN Feature
st.markdown(f"<div class='translate-banner'>🌐 Translating: Live → {st.session_state.my_listen}</div>", unsafe_allow_html=True)
st.session_state.my_listen=st.selectbox("Nenu Vinalanukune Bhasha / I Listen:", ["Telugu","Hindi","Tamil","English"], index=["Telugu","Hindi","Tamil","English"].index(st.session_state.my_listen), label_visibility="collapsed")

# --- 9 BUTTONS LIKE REAL DIALER ---
st.write("")
r1c1,r1c2,r1c3=st.columns(3)
with r1c1:
    if st.button("📝", key="n1"): st.toast("Notes")
    st.markdown("<div class='control-label'>Notes</div>", unsafe_allow_html=True)
with r1c2:
    if st.button("➕", key="n2"): st.toast(f"Invite Code: {st.session_state.room}")
    st.markdown("<div class='control-label'>Add call</div>", unsafe_allow_html=True)
with r1c3:
    if st.button("🔇", key="n3"): st.toast("Mute ON")
    st.markdown("<div class='control-label'>Mute</div>", unsafe_allow_html=True)

r2c1,r2c2,r2c3=st.columns(3)
with r2c1:
    st.button("🌐", key="lang", help="Language ON", disabled=True)
    st.markdown("<div class='control-label' style='color:#10b981!important;font-weight:700'>Language ON</div>", unsafe_allow_html=True)
with r2c2:
    if st.button("📹", key="n5"): st.toast("Video soon")
    st.markdown("<div class='control-label'>Video</div>", unsafe_allow_html=True)
with r2c3:
    if st.button("⏸️", key="n6"): st.toast("Hold")
    st.markdown("<div class='control-label'>Hold</div>", unsafe_allow_html=True)

r3c1,r3c2,r3c3=st.columns(3)
with r3c1:
    if st.button("⌨️", key="n7"): st.toast("Keypad")
    st.markdown("<div class='control-label'>Keypad</div>", unsafe_allow_html=True)
with r3c2:
    if st.button("📞", key="end"):
        st.session_state.room=None
        st.rerun()
    st.markdown("<div class='control-label' style='color:#ef4444!important'>End call</div>", unsafe_allow_html=True)
with r3c3:
    if st.button("🔊", key="n9"): st.toast("Speaker ON")
    st.markdown("<div class='control-label'>Speaker</div>", unsafe_allow_html=True)

st.divider()

# --- STEP 1: THE ONLY MIC - 100% STABLE ---
st.markdown("### 🎙️ Tap to Speak - Auto Translate")
st.caption("Nuvvu matladina ventane avathali phone lo auto vinipisthundi - Phone call laaga")

audio = st.audio_input("Mic nokki matladu, aapagane auto translate avuthundi", key="live_mic", label_visibility="collapsed")

if audio:
    temp_path=f"room_data/{st.session_state.room}_{st.session_state.my_id}_{int(time.time())}.wav"
    with open(temp_path,"wb") as f: f.write(audio.getbuffer())
    
    with st.spinner(f"Translating... → Broadcasting to {st.session_state.room}"):
        try:
            with open(temp_path,"rb") as f:
                stt_res = client.speech_to_text.transcribe(file=f, model="saaras:v3")
                orig = getattr(stt_res, 'transcript', '') or str(stt_res)
            
            if orig and len(orig.strip())>1:
                st.info(f"You said: {orig}")
                # Supabase Broadcast - Real-time for other phones
                supabase.table("broadcasts").insert({
                    "room_id": st.session_state.room,
                    "sender_id": st.session_state.my_id,
                    "text": orig,
                    "src_lang": lang_map[st.session_state.my_speak],
                    "src_name": st.session_state.my_speak
                }).execute()
                st.success(f"✅ Sent to {st.session_state.room}! Vere phone lo 2 sec lo auto play avuthundi")
            else:
                st.warning("Voice clear ga ledu, malli try chey")
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

# --- LIVE INCOMING - SUPABASE REALTIME ---
@st.fragment(run_every=1)
def live_incoming():
    st.markdown(f"### 🔊 Live Incoming - {st.session_state.my_listen} lo")
    st.caption("Auto refresh - vere phone matladithe 1 sec lo vastundi")
    
    try:
        # Get latest message from other users in same room
        res=supabase.table("broadcasts").select("*").eq("room_id", st.session_state.room).neq("sender_id", st.session_state.my_id).order("created_at", desc=True).limit(3).execute()
        
        if not res.data:
            st.info(f"No messages yet in {st.session_state.room}. Vere phone same code tho join avvali.")
            return
        
        for r in res.data:
            if time.time() - 600 > 0: # we need timestamp parse, skip for now
                pass
            orig_text=r["text"]
            sender=r["sender_id"]
            tgt_code=lang_map[st.session_state.my_listen]
            
            cache_audio=f"room_data/live_{st.session_state.room}_{st.session_state.my_id}_{r['id']}.wav"
            cache_txt=f"room_data/live_{st.session_state.room}_{st.session_state.my_id}_{r['id']}.txt"
            
            if not os.path.exists(cache_audio):
                try:
                    # Auto detect + Translate
                    trans_res = client.text.translate(input=orig_text, source_language_code="auto", target_language_code=tgt_code, model="mayura:v1")
                    translated = getattr(trans_res, 'translated_text', orig_text)
                    open(cache_txt,"w",encoding="utf-8").write(f"{orig_text} → {translated}")
                    # TTS
                    tts_res = client.text_to_speech.convert(text=translated, target_language_code=tgt_code, model="bulbul:v3")
                    ab64 = tts_res.audios[0] if hasattr(tts_res,'audios') else None
                    if ab64:
                        data=base64.b64decode(ab64)
                        open(cache_audio,"wb").write(data)
                except Exception as e:
                    st.error(f"Translate error: {e}")
                    continue
            
            if os.path.exists(cache_audio):
                info=open(cache_txt,"r",encoding="utf-8").read() if os.path.exists(cache_txt) else orig_text
                st.markdown(f"<div class='incoming-card'>👤 <b>{sender}:</b> {info}</div>", unsafe_allow_html=True)
                st.audio(cache_audio, autoplay=True)
    
    except Exception as e:
        st.error(f"Supabase error: {e} - Check URL/Key")

live_incoming()
