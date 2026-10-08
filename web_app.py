import os
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="SAMBOT X")

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
<div class="profile"><div class="avatar">S</div><div><b>Sambot User</b><div style="font-size:10px;opacity:.4">Personal</div></div></div>
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

<script>
const box=document.getElementById('box'),chat=document.getElementById('chat'),historyEl=document.getElementById('history'),sidebar=document.getElementById('sidebar');
let sessions=JSON.parse(localStorage.getItem('sambot_sessions')||'[]'), currentId=localStorage.getItem('sambot_current')||'';
let theme=localStorage.getItem('sambot_theme')||'dark';
if(theme==='light')document.body.classList.add('light');
function save(){localStorage.setItem('sambot_sessions',JSON.stringify(sessions));localStorage.setItem('sambot_current',currentId)}
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
function imageRequest(s){return /\\b(create|generate|make|draw|render)\\s+(an?\\s+)?image\\b/i.test(s)||/^\\/image\\b/i.test(s)}
function imagePrompt(s){return s.replace(/^\\/image\\s*/i,'').replace(/^\\s*(create|generate|make|draw|render)\\s+(an?\\s+)?image\\s*(of|showing)?\\s*/i,'').trim()||s}
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
ensure();renderHistory();renderChat();
</script>
</body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/health")
def health():
    return {
        "ok": True,
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "cloudflare_configured": bool(os.getenv("CLOUDFLARE_ACCOUNT_ID") and os.getenv("CLOUDFLARE_API_TOKEN"))
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
