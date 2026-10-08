import os
import requests
import sqlite3
import secrets
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from fastapi import Request
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="SAMBOT X")

DB_PATH=os.getenv("SAMBOT_DB_PATH","sambot.db")
SESSIONS={}

def db():
    con=sqlite3.connect(DB_PATH)
    con.row_factory=sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS signup_otps (email TEXT PRIMARY KEY,name TEXT NOT NULL,password_hash TEXT NOT NULL,otp_hash TEXT NOT NULL,expires_at TEXT NOT NULL)")
    con.commit()
    return con

def hash_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,210000)
    return salt.hex()+":"+digest.hex()

def verify_password(password,stored):
    try:
        salt,digest=stored.split(":")
        check=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),210000).hex()
        return secrets.compare_digest(check,digest)
    except Exception:
        return False

def current_user(request):
    token=request.cookies.get("sambot_session")
    uid=SESSIONS.get(token)
    if not uid:
        return None
    con=db()
    row=con.execute("SELECT id,name,email FROM users WHERE id=?",(uid,)).fetchone()
    con.close()
    return dict(row) if row else None


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

class ImageRequest(BaseModel):
    prompt: str

HTML = r"""<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAMBOT X</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#08090c;color:#f5f5f5;height:100vh;overflow:hidden}
button,input,textarea{font:inherit}.app{height:100vh;display:flex}.sidebar{width:280px;background:#0e1014;border-right:1px solid #252831;display:flex;flex-direction:column;padding:12px;flex-shrink:0}.brand{font-weight:800;font-size:19px;padding:8px}.brand small{opacity:.4;font-size:9px;margin-left:5px}.new{width:100%;border:1px solid #30343d;background:#171a20;color:#fff;border-radius:10px;padding:11px;text-align:left;cursor:pointer;font-weight:700}.new:hover,.chatitem:hover,.sidebtn:hover{background:#20242c}.search{margin:10px 0}.search input{width:100%;background:#171a20;border:1px solid #2c3038;color:#fff;border-radius:9px;padding:9px 10px;outline:0}.history-title{font-size:10px;color:#777b86;padding:7px}.history{flex:1;overflow:auto}.chatitem{display:flex;align-items:center;gap:6px;padding:9px 7px;border-radius:9px;cursor:pointer;margin:2px 0}.chatitem.active{background:#242832}.chatname{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;font-size:13px}.menu{border:0;background:transparent;color:#999;cursor:pointer}.sidebottom{border-top:1px solid #252831;padding-top:8px}.sidebtn{width:100%;background:transparent;border:0;color:#ddd;text-align:left;padding:10px 8px;border-radius:9px;cursor:pointer}.profile{display:flex;align-items:center;gap:9px;padding:10px 6px}.avatar{width:30px;height:30px;border-radius:50%;background:#303641;display:grid;place-items:center}.main{flex:1;min-width:0;display:flex;flex-direction:column}.topbar{height:62px;border-bottom:1px solid #252831;display:flex;align-items:center;justify-content:space-between;padding:0 18px}.model{font-weight:700}.status{font-size:10px;opacity:.4;margin-left:7px}.top-actions{display:flex;gap:7px}.iconbtn,.toolbtn{border:1px solid #2c3038;background:#15181e;color:#ddd;border-radius:9px;padding:8px 10px;cursor:pointer}.chat{flex:1;overflow:auto;padding:28px 20px 150px}.empty{max-width:720px;margin:12vh auto;text-align:center}.empty h1{font-size:38px;margin:0 0 9px}.empty p{opacity:.45}.row{display:flex;margin:16px 0}.row.user{justify-content:flex-end}.wrap{max-width:min(820px,88%)}.msg{padding:14px 16px;border-radius:18px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere;background:#15181e}.user .msg{background:#2c3039}.actions{display:flex;gap:5px;margin-top:6px}.mini{font-size:11px;border:1px solid #292d35;background:transparent;color:#999;border-radius:7px;padding:4px 7px;cursor:pointer}.image-result{display:block;max-width:100%;border-radius:14px}.thinking{opacity:.55}.composer{position:fixed;bottom:0;left:280px;right:0;display:flex;justify-content:center;padding:12px 18px 18px;background:linear-gradient(transparent,#08090c 25%)}.compose{width:min(900px,100%);background:#15181e;border:1px solid #343842;border-radius:18px;padding:10px;box-shadow:0 10px 35px #0009}.compose textarea{width:100%;min-height:48px;max-height:180px;resize:none;background:transparent;border:0;outline:0;color:#fff;padding:8px}.controls{display:flex;justify-content:space-between;gap:8px}.tools{display:flex;gap:6px}.toolbtn{padding:7px 10px;font-size:12px}.send{background:#fff;color:#000;font-weight:700}.modal{position:fixed;inset:0;background:#0009;display:none;align-items:center;justify-content:center;z-index:50}.modal.show{display:flex}.panel{width:min(500px,92%);background:#171a20;border:1px solid #343842;border-radius:16px;padding:20px}.panel h2{margin-top:0}.panel label{display:block;font-size:12px;opacity:.65;margin:14px 0 6px}.panel input{width:100%;background:#0e1014;border:1px solid #30343d;color:#fff;border-radius:8px;padding:10px}.panel button{margin-top:12px}.mobile{display:none}
.light{background:#f7f7f8;color:#111}.light .sidebar,.light .topbar,.light .compose,.light .msg,.light .new,.light .search input,.light .iconbtn,.light .toolbtn,.light .panel{background:#fff;color:#111}.light .sidebar,.light .topbar{border-color:#ddd}.light textarea{color:#111}.light .user .msg{background:#e4e5e8}.light .chatitem:hover{background:#eee}
@media(max-width:760px){.sidebar{position:fixed;z-index:40;left:-292px;top:0;bottom:0;transition:.2s}.sidebar.open{left:0}.composer{left:0}.mobile{display:inline-block}.topbar{height:58px}.empty h1{font-size:28px}}
</style>
</head>
<body>
<div id="auth" style="position:fixed;inset:0;background:#08090c;display:flex;align-items:center;justify-content:center;z-index:100">
<div style="width:min(410px,92%);background:#15181e;border:1px solid #343842;border-radius:18px;padding:25px">
<div style="font-size:25px;font-weight:800">✨ SAMBOT X</div><div style="opacity:.5;font-size:12px;margin:5px 0 20px">Your personal AI assistant</div>
<div style="display:flex;gap:6px;margin-bottom:12px"><button class="toolbtn" onclick="authMode(false)">Login</button><button class="toolbtn" onclick="authMode(true)">Sign up</button></div>
<input id="authName" placeholder="Name" style="display:none;width:100%;padding:11px;margin-bottom:8px;background:#0e1014;color:#fff;border:1px solid #30343d;border-radius:8px">
<input id="authEmail" type="email" placeholder="Email" style="width:100%;padding:11px;margin-bottom:8px;background:#0e1014;color:#fff;border:1px solid #30343d;border-radius:8px">
<input id="authPassword" type="password" placeholder="Password (6+ characters)" style="width:100%;padding:11px;background:#0e1014;color:#fff;border:1px solid #30343d;border-radius:8px">
<div id="otpBox" style="display:none;margin-top:10px">
<input id="authOtp" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6-digit OTP" style="width:100%;padding:11px;background:#0e1014;color:#fff;border:1px solid #30343d;border-radius:8px;text-align:center;letter-spacing:5px">
<button id="otpVerify" class="toolbtn send" style="width:100%;margin-top:8px" onclick="verifySignupOtp()">Verify OTP</button>
<button class="toolbtn" style="width:100%;margin-top:6px" onclick="resendSignupOtp()">Resend OTP</button>
</div>
<button id="authSubmit" class="toolbtn send" style="width:100%;margin-top:10px" onclick="submitAuth()">Login</button>
<div id="authMsg" style="font-size:12px;margin-top:9px;color:#ff8b8b"></div>
</div></div>
<div class="app">
<aside class="sidebar" id="sidebar">
<div class="brand">✨ SAMBOT X <small>AI ASSISTANT</small></div>
<button class="new" onclick="newChat()">＋ New chat</button>
<div class="search"><input id="search" placeholder="🔎 Search chats..." oninput="renderHistory()"></div>
<div class="history-title">CHAT HISTORY</div>
<div class="history" id="history"></div>
<div class="sidebottom">
<button class="sidebtn" onclick="openSettings()">⚙ Settings</button>
<button class="sidebtn" onclick="exportChats()">⇩ Export chats</button>
<button class="sidebtn" onclick="toggleTheme()">☼ Appearance</button>
<div class="profile"><div class="avatar" id="avatar">S</div><div><b id="profileName">Sambot User</b><div id="profileEmail" style="font-size:10px;opacity:.4">Personal</div></div><button class="menu" onclick="logout()">↪</button></div>
</div>
</aside>
<section class="main">
<header class="topbar">
<div><button class="iconbtn mobile" onclick="toggleSidebar()">☰</button><span class="model">SAMBOT X</span><span class="status">Groq + Cloudflare AI</span></div>
<div class="top-actions"><button class="iconbtn" onclick="newChat()">＋ New</button></div>
</header>
<section class="chat" id="chat"></section>
<div class="composer"><div class="compose">
<textarea id="box" rows="2" placeholder="Message Sambot X..."></textarea>
<div class="controls"><div class="tools"><button class="toolbtn" id="mic" onclick="voice()">🎙 Voice</button></div><div class="tools"><button class="toolbtn send" onclick="send()">Send ➤</button></div></div>
<div style="text-align:center;font-size:10px;opacity:.35;padding:5px">Enter to send • Shift+Enter for new line • Type “create image …” for images</div>
</div></div>
</section>
</div>

<div class="modal" id="settings"><div class="panel">
<h2>⚙ Settings</h2>
<label>Display name</label><input id="displayName" placeholder="Sambot User">
<label>About</label><div style="opacity:.55;font-size:12px">SAMBOT X • Groq chat • Cloudflare image generation</div>
<button class="toolbtn" onclick="saveSettings()">Save</button>
<button class="toolbtn" onclick="closeSettings()">Close</button>
</div></div>

<script>let signupMode=false,otpPending=false;
function authMode(signup){
signupMode=signup;otpPending=false;
document.getElementById('authName').style.display=signup?'block':'none';
document.getElementById('authPassword').style.display='block';
document.getElementById('otpBox').style.display='none';
document.getElementById('authSubmit').style.display='block';
document.getElementById('authSubmit').textContent=signup?'Create account':'Login';
document.getElementById('authMsg').textContent='';
document.getElementById('authOtp').value='';
}
async function submitAuth(){
const name=document.getElementById('authName').value.trim();
const email=document.getElementById('authEmail').value.trim();
const password=document.getElementById('authPassword').value;
const msg=document.getElementById('authMsg');
if(!email||!password||(signupMode&&!name)){msg.textContent='Please fill all fields.';return}
msg.style.color='#ff8b8b';msg.textContent='Please wait…';
const endpoint=signupMode?'/api/signup':'/api/login';
const payload=signupMode?{name,email,password}:{email,password};
try{
const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
const j=await r.json();
if(!r.ok||j.error){msg.textContent=j.error||'Something went wrong.';return}
if(signupMode){
otpPending=true;
document.getElementById('authOtp').value='';
document.getElementById('otpBox').style.display='block';
document.getElementById('authSubmit').style.display='none';
msg.style.color='#9fe3a1';
msg.textContent='OTP sent to your email. Enter the 6-digit code below.';
return;
}
if(j.user){document.getElementById('auth').style.display='none';setUser(j.user)}
}catch(e){msg.textContent='Connection error: '+e.message}
}
async function verifySignupOtp(){
if(!otpPending)return;
const email=document.getElementById('authEmail').value.trim();
const token=document.getElementById('authOtp').value.trim();
const msg=document.getElementById('authMsg');
if(!/^\d{6}$/.test(token)){msg.style.color='#ff8b8b';msg.textContent='Enter the 6-digit OTP from your email.';return}
msg.style.color='#aaa';msg.textContent='Verifying OTP…';
try{
const r=await fetch('/api/verify-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,otp:token})});
const j=await r.json();
if(!r.ok||j.error){msg.style.color='#ff8b8b';msg.textContent=j.error||'Invalid OTP.';return}
if(j.user){otpPending=false;document.getElementById('auth').style.display='none';setUser(j.user)}
}catch(e){msg.style.color='#ff8b8b';msg.textContent='Connection error: '+e.message}
}
async function resendSignupOtp(){
const email=document.getElementById('authEmail').value.trim();
const msg=document.getElementById('authMsg');
if(!email){msg.textContent='Enter your email first.';return}
msg.style.color='#aaa';msg.textContent='Sending a new OTP…';
try{
const r=await fetch('/api/resend-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
const j=await r.json();
if(!r.ok||j.error){msg.style.color='#ff8b8b';msg.textContent=j.error||'Could not resend OTP.';return}
msg.style.color='#9fe3a1';msg.textContent='A new OTP has been sent.';
}catch(e){msg.style.color='#ff8b8b';msg.textContent='Connection error: '+e.message}
}
function setUser(u){const name=u.name||u.email?.split('@')[0]||'Sambot User';document.getElementById('profileName').textContent=name;document.getElementById('profileEmail').textContent=u.email||'';document.getElementById('avatar').textContent=name.charAt(0).toUpperCase()}
async function checkAuth(){
try{
const r=await fetch('/api/me');
const j=await r.json();
if(j.user){document.getElementById('auth').style.display='none';setUser(j.user)}
else document.getElementById('auth').style.display='flex';
}catch(e){document.getElementById('auth').style.display='flex'}
}
async function logout(){await fetch('/api/logout',{method:'POST'});location.reload()}


const box=document.getElementById('box'),chat=document.getElementById('chat'),historyEl=document.getElementById('history'),sidebar=document.getElementById('sidebar');
let sessions=[];try{sessions=JSON.parse(localStorage.getItem('sambot_sessions')||'[]');if(!Array.isArray(sessions))sessions=[]}catch(e){localStorage.removeItem('sambot_sessions');sessions=[]}let currentId=localStorage.getItem('sambot_current')||'';
let theme=localStorage.getItem('sambot_theme')||'dark';
if(theme==='light')document.body.classList.add('light');
function save(){try{localStorage.setItem('sambot_sessions',JSON.stringify(sessions));localStorage.setItem('sambot_current',currentId)}catch(e){console.warn('Storage unavailable',e)}}
function current(){return sessions.find(x=>x.id===currentId)}
function titleFor(s){return s.title||((s.messages.find(m=>m.role==='user')||{}).content||'New chat').slice(0,36)}
function ensure(){if(!currentId||!current()){currentId=Date.now().toString();sessions.unshift({id:currentId,title:'New chat',messages:[]});save()}}
function renderHistory(){ensure();const q=(document.getElementById('search').value||'').toLowerCase();historyEl.innerHTML='';sessions.filter(s=>titleFor(s).toLowerCase().includes(q)).forEach(s=>{const d=document.createElement('div');d.className='chatitem '+(s.id===currentId?'active':'');const n=document.createElement('span');n.className='chatname';n.textContent=titleFor(s);n.onclick=()=>loadChat(s.id);const m=document.createElement('button');m.className='menu';m.textContent='⋯';m.onclick=e=>{e.stopPropagation();chatMenu(s.id)};d.append(n,m);historyEl.appendChild(d)})}
function renderChat(){chat.innerHTML='';const s=current();if(!s||!s.messages.length){chat.innerHTML='<div class="empty"><h1>How can I help?</h1><p>Chat, code, write, study, brainstorm — or type <b>create image</b>.</p></div>';return} s.messages.forEach(m=>drawMessage(m))}
function drawMessage(m){const row=document.createElement('div');row.className='row '+m.role;const wrap=document.createElement('div');wrap.className='wrap';const msg=document.createElement('div');msg.className='msg';if(m.image){const img=document.createElement('img');img.className='image-result';img.src=m.image;msg.appendChild(img)}else msg.textContent=m.content||'';wrap.appendChild(msg);if(m.role==='assistant'&&!m.image){const acts=document.createElement('div');acts.className='actions';const cp=document.createElement('button');cp.className='mini';cp.textContent='Copy';cp.onclick=()=>navigator.clipboard?.writeText(m.content||'');acts.appendChild(cp);const sp=document.createElement('button');sp.className='mini';sp.textContent='🔊';sp.onclick=()=>speakText(m.content||'');acts.appendChild(sp);const rg=document.createElement('button');rg.className='mini';rg.textContent='↻ Regenerate';rg.onclick=()=>regenerate();acts.appendChild(rg);wrap.appendChild(acts)}row.appendChild(wrap);chat.appendChild(row)}
function loadChat(id){currentId=id;save();renderHistory();renderChat();sidebar.classList.remove('open')}
function newChat(){currentId=Date.now().toString();sessions.unshift({id:currentId,title:'New chat',messages:[]});save();renderHistory();renderChat();box.focus()}
function chatMenu(id){const s=sessions.find(x=>x.id===id);if(!s)return;const action=prompt('Type rename or delete');if(action==='rename'){const n=prompt('New chat name',titleFor(s));if(n){s.title=n;save();renderHistory()}}else if(action==='delete'){if(confirm('Delete this chat?')){sessions=sessions.filter(x=>x.id!==id);if(currentId===id)currentId='';ensure();save();renderHistory();renderChat()}}}
function add(role,content,image){const s=current();s.messages.push({role,content,image});if(role==='user'&&s.title==='New chat')s.title=content.slice(0,36);save();drawMessage({role,content,image});chat.scrollTop=chat.scrollHeight;renderHistory()}
function imageRequest(s){return /\b(create|generate|make|draw|render)\s+(an?\s+)?image\b/i.test(s)||/^\/image\b/i.test(s)}
function imagePrompt(s){return s.replace(/^\/image\s*/i,'').replace(/^\s*(create|generate|make|draw|render)\s+(an?\s+)?image\s*(of|showing)?\s*/i,'').trim()||s}
async function send(){const text=box.value.trim();if(!text)return;box.value='';if(imageRequest(text)){await generateImage(imagePrompt(text),text);return}add('user',text);const thinking={role:'assistant',content:'Thinking…'};drawMessage(thinking);chat.lastElementChild.querySelector('.msg').classList.add('thinking');try{const msgs=current().messages.filter(m=>!m.image&&m.content!=='Thinking…').slice(-20).map(m=>({role:m.role,content:m.content}));const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:msgs})});const j=await r.json();chat.removeChild(chat.lastElementChild);add('assistant',j.reply||j.error||'Something went wrong.')}catch(e){chat.removeChild(chat.lastElementChild);add('assistant','Connection error: '+e.message)}}
async function generateImage(prompt,shown){add('user',shown);add('assistant','Creating your image…');const row=chat.lastElementChild;row.querySelector('.msg').classList.add('thinking');try{const r=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});const j=await r.json();chat.removeChild(row);if(j.image)add('assistant','',j.image);else add('assistant',j.error||'Image generation failed.')}catch(e){chat.removeChild(row);add('assistant','Image error: '+e.message)}}
async function regenerate(){const s=current();const last=s.messages.filter(m=>m.role==='user'&&!m.image).pop();if(!last)return;s.messages=s.messages.slice(0,-1);save();renderChat();box.value=last.content;await send()}
function voice(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R){alert('Voice input is not supported in this browser.');return}const rec=new R();rec.lang='en-IN';rec.interimResults=false;const b=document.getElementById('mic');b.textContent='⏺ Listening…';rec.onresult=e=>box.value=e.results[0][0].transcript;rec.onend=()=>b.textContent='🎙 Voice';rec.onerror=()=>b.textContent='🎙 Voice';rec.start()}
function speakText(t){if('speechSynthesis'in window){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(t))}}
function toggleTheme(){theme=theme==='dark'?'light':'dark';localStorage.setItem('sambot_theme',theme);document.body.classList.toggle('light',theme==='light')}
function toggleSidebar(){sidebar.classList.toggle('open')}
function openSettings(){document.getElementById('settings').classList.add('show');document.getElementById('displayName').value=localStorage.getItem('sambot_name')||'Sambot User'}
function closeSettings(){document.getElementById('settings').classList.remove('show')}
function saveSettings(){localStorage.setItem('sambot_name',document.getElementById('displayName').value||'Sambot User');closeSettings()}
function exportChats(){const blob=new Blob([JSON.stringify(sessions,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='sambot-chats.json';a.click();URL.revokeObjectURL(a.href)}
box.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}})
window.authMode=authMode;window.submitAuth=submitAuth;window.logout=logout;window.newChat=newChat;window.send=send;window.toggleTheme=toggleTheme;window.openSettings=openSettings;window.closeSettings=closeSettings;window.saveSettings=saveSettings;window.exportChats=exportChats;window.toggleSidebar=toggleSidebar;window.voice=voice;window.regenerate=regenerate;window.chatMenu=chatMenu;window.loadChat=loadChat;ensure();renderHistory();renderChat();authMode(false);checkAuth();
</script>
</body></html>"""

def smtp_send_otp(email, otp):
    sender=os.getenv("GMAIL_SMTP_USER","").strip()
    app_password=os.getenv("GMAIL_SMTP_APP_PASSWORD","").replace(" ","").strip()
    if not sender or not app_password:
        raise RuntimeError("Gmail SMTP is not configured in Render. Add GMAIL_SMTP_USER and GMAIL_SMTP_APP_PASSWORD.")
    msg=EmailMessage()
    msg["Subject"]="Your SAMBOT X verification code"
    msg["From"]=f"SAMBOT X <{sender}>"
    msg["To"]=email
    msg.set_content(f"""Your SAMBOT X verification code is: {otp}

This code expires in 10 minutes.

If you did not create a SAMBOT X account, you can ignore this email.
""")
    with smtplib.SMTP("smtp.gmail.com",587,timeout=30) as server:
        server.starttls()
        server.login(sender,app_password)
        server.send_message(msg)

def make_otp():
    return f"{secrets.randbelow(1000000):06d}"

def otp_hash(email,otp):
    return hashlib.sha256(f"{email.lower()}:{otp}".encode()).hexdigest()

@app.post("/api/signup")
def signup(data: dict):
    name=str(data.get("name","")).strip()
    email=str(data.get("email","")).strip().lower()
    password=str(data.get("password",""))
    if not name or "@" not in email or len(password)<6:
        return JSONResponse({"error":"Enter a name, valid email, and password of at least 6 characters."},status_code=400)
    con=db()
    existing=con.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone()
    if existing:
        con.close()
        return JSONResponse({"error":"An account with that email already exists. Please log in."},status_code=409)
    otp=make_otp()
    expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
    con.execute("INSERT OR REPLACE INTO signup_otps(email,name,password_hash,otp_hash,expires_at) VALUES(?,?,?,?,?)",
                (email,name,hash_password(password),otp_hash(email,otp),expires))
    con.commit()
    con.close()
    try:
        smtp_send_otp(email,otp)
    except Exception as e:
        con=db()
        con.execute("DELETE FROM signup_otps WHERE email=?",(email,))
        con.commit()
        con.close()
        return JSONResponse({"error":f"Could not send OTP email: {e}"},status_code=500)
    return {"ok":True,"otp_required":True}

@app.post("/api/verify-otp")
def verify_otp(data: dict):
    email=str(data.get("email","")).strip().lower()
    otp=str(data.get("otp","")).strip()
    if "@" not in email or not otp.isdigit() or len(otp)!=6:
        return JSONResponse({"error":"Enter the 6-digit OTP."},status_code=400)
    con=db()
    row=con.execute("SELECT * FROM signup_otps WHERE email=?",(email,)).fetchone()
    if not row:
        con.close()
        return JSONResponse({"error":"No pending signup found. Please sign up again."},status_code=400)
    try:
        expires=datetime.fromisoformat(row["expires_at"])
    except Exception:
        expires=datetime.now(timezone.utc)-timedelta(seconds=1)
    if datetime.now(timezone.utc)>expires:
        con.execute("DELETE FROM signup_otps WHERE email=?",(email,))
        con.commit()
        con.close()
        return JSONResponse({"error":"OTP expired. Please request a new one."},status_code=400)
    if not secrets.compare_digest(otp_hash(email,otp),row["otp_hash"]):
        con.close()
        return JSONResponse({"error":"Incorrect OTP. Please try again."},status_code=400)
    try:
        cur=con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",(row["name"],email,row["password_hash"]))
        con.execute("DELETE FROM signup_otps WHERE email=?",(email,))
        con.commit()
        uid=cur.lastrowid
    except sqlite3.IntegrityError:
        con.close()
        return JSONResponse({"error":"An account with that email already exists. Please log in."},status_code=409)
    con.close()
    token=secrets.token_urlsafe(32)
    SESSIONS[token]=uid
    out=JSONResponse({"ok":True,"user":{"id":uid,"name":row["name"],"email":email}})
    out.set_cookie("sambot_session",token,httponly=True,samesite="lax",secure=True,max_age=2592000)
    return out

@app.post("/api/resend-otp")
def resend_otp(data: dict):
    email=str(data.get("email","")).strip().lower()
    if "@" not in email:
        return JSONResponse({"error":"Enter a valid email."},status_code=400)
    con=db()
    row=con.execute("SELECT * FROM signup_otps WHERE email=?",(email,)).fetchone()
    if not row:
        con.close()
        return JSONResponse({"error":"No pending signup found. Please sign up again."},status_code=400)
    otp=make_otp()
    expires=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
    con.execute("UPDATE signup_otps SET otp_hash=?,expires_at=? WHERE email=?",(otp_hash(email,otp),expires,email))
    con.commit()
    con.close()
    try:
        smtp_send_otp(email,otp)
    except Exception as e:
        return JSONResponse({"error":f"Could not send OTP email: {e}"},status_code=500)
    return {"ok":True}

@app.post("/api/login")
def login(data: dict):
    email=str(data.get("email","")).strip().lower()
    password=str(data.get("password",""))
    con=db()
    user=con.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    con.close()
    if not user or not verify_password(password,user["password_hash"]):
        return {"error":"Incorrect email or password."}
    token=secrets.token_urlsafe(32)
    SESSIONS[token]=user["id"]
    out=JSONResponse({"ok":True,"user":{"id":user["id"],"name":user["name"],"email":user["email"]}})
    out.set_cookie("sambot_session",token,httponly=True,samesite="lax",secure=True,max_age=2592000)
    return out

@app.get("/api/me")
def me(request: Request):
    return {"user":current_user(request)}

@app.post("/api/logout")
def logout(request: Request):
    token=request.cookies.get("sambot_session")
    SESSIONS.pop(token,None)
    out=JSONResponse({"ok":True})
    out.delete_cookie("sambot_session")
    return out

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/health")
def health():
    return {
        "ok": True,
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "cloudflare_configured": bool(os.getenv("CLOUDFLARE_ACCOUNT_ID") and os.getenv("CLOUDFLARE_API_TOKEN")),
        "gmail_smtp_configured": bool(os.getenv("GMAIL_SMTP_USER") and os.getenv("GMAIL_SMTP_APP_PASSWORD"))
    }

@app.post("/api/image")
def image(req: ImageRequest):
    account=os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token=os.getenv("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        return {"error":"Cloudflare image generation is not configured in Render."}
    url=f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        r=requests.post(
            url,
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json","Accept":"application/json"},
            json={"prompt":req.prompt,"steps":4},
            timeout=120,
        )
        if not r.ok:
            try: err=r.json()
            except Exception: err=r.text[:1000]
            return {"error":f"Cloudflare returned HTTP {r.status_code}: {err}"}
        try: data=r.json()
        except Exception: return {"error":f"Cloudflare returned a non-JSON response (HTTP {r.status_code})."}
        image_b64=data.get("result",{}).get("image")
        if not image_b64:
            return {"error":f"Cloudflare response did not contain an image: {data}"}
        return {"image":f"data:image/jpeg;base64,{image_b64}"}
    except requests.Timeout:
        return {"error":"Cloudflare image generation timed out. Please try again."}
    except Exception as e:
        return {"error":f"Cloudflare image generation failed: {type(e).__name__}: {e}"}

@app.post("/api/chat")
def chat(req: ChatRequest):
    key=os.getenv("GROQ_API_KEY")
    if not key:
        return {"error":"GROQ_API_KEY is not configured in Render."}
    try:
        client=Groq(api_key=key)
        messages=[{"role":m.role,"content":m.content} for m in req.messages if m.role in ("user","assistant")][-20:]
        r=client.chat.completions.create(
            model=os.getenv("GROQ_MODEL","openai/gpt-oss-120b"),
            messages=[{"role":"system","content":"You are Sambot X, a highly capable helpful AI assistant. Answer naturally, accurately, and clearly. Help with coding, writing, studying, brainstorming, math, explanations, and general tasks. If the user asks to create/generate an image, the web app handles that separately."}]+messages,
            temperature=0.7,
            max_tokens=1200,
        )
        return {"reply":r.choices[0].message.content}
    except Exception as e:
        return {"error":f"Groq error: {e}"}
