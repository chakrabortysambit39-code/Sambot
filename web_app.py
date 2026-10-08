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
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#08090c;color:#f5f5f5}
main{max-width:1100px;margin:auto;height:100vh;display:flex;flex-direction:column}
header{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 18px;border-bottom:1px solid #24262d;background:#0b0c10;position:sticky;top:0;z-index:2}
.brand{font-size:20px;font-weight:800}.tag{opacity:.5;font-size:11px;margin-left:8px}.actions{display:flex;gap:8px}
.topbtn,.toolbtn{border:1px solid #2a2d35;background:#15171d;color:#eee;border-radius:10px;padding:9px 12px;cursor:pointer}.topbtn:hover,.toolbtn:hover{background:#20232b}
.chat{flex:1;overflow:auto;padding:26px 20px 130px}
.row{display:flex;margin:14px 0}.row.user{justify-content:flex-end}.msg{max-width:min(820px,85%);padding:14px 16px;border-radius:18px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}.user .msg{background:#2c303a}.assistant .msg{background:#15171d}
.meta{font-size:10px;opacity:.4;margin:5px 4px}.message-actions{display:flex;gap:6px;margin-top:7px}.mini{font-size:11px;border:1px solid #292c34;background:transparent;color:#aaa;border-radius:8px;padding:5px 8px;cursor:pointer}
.image-result{display:block;max-width:100%;width:auto;border-radius:14px;margin-top:5px}.thinking{opacity:.6}
.composer{position:fixed;bottom:0;left:0;right:0;display:flex;justify-content:center;padding:12px 16px 18px;background:linear-gradient(transparent,#08090c 22%)}
.compose-inner{width:min(1050px,100%);background:#15171d;border:1px solid #30333c;border-radius:18px;padding:10px;box-shadow:0 10px 35px #0008}
textarea{width:100%;resize:none;min-height:48px;max-height:180px;background:transparent;color:white;border:0;outline:0;padding:8px 9px;font:inherit}
.controls{display:flex;align-items:center;justify-content:space-between;gap:8px}.left-tools,.right-tools{display:flex;gap:7px}.toolbtn{padding:7px 10px;font-size:12px}.send{background:#fff;color:#000;border-color:#fff;font-weight:700}.mic.active{background:#d33;color:#fff}
.hint{text-align:center;opacity:.35;font-size:11px;padding:5px}.empty{max-width:720px;margin:15vh auto;text-align:center}.empty h1{font-size:36px;margin:0 0 10px}.empty p{opacity:.5}
@media(max-width:650px){header{height:58px}.tag{display:none}.chat{padding:18px 12px 125px}.msg{max-width:92%}.empty h1{font-size:28px}.topbtn{padding:7px 9px}}
</style>
</head>
<body>
<main>
<header>
<div class="brand">✨ SAMBOT X <span class="tag">Groq + Cloudflare AI</span></div>
<div class="actions"><button class="topbtn" onclick="newChat()">＋ New chat</button><button class="topbtn" onclick="toggleTheme()">☼</button></div>
</header>
<section id="chat" class="chat">
<div class="empty" id="empty"><h1>How can I help?</h1><p>Chat, code, write, explain, brainstorm — or type <b>create image</b> to generate an image.</p></div>
</section>
<div class="composer"><div class="compose-inner">
<textarea id="box" rows="2" placeholder="Message Sambot X..."></textarea>
<div class="controls">
<div class="left-tools"><button class="toolbtn mic" id="mic" onclick="voice()">🎙 Voice</button><button class="toolbtn" onclick="clearChat()">Clear</button></div>
<div class="right-tools"><button class="toolbtn send" onclick="send()">Send ➤</button></div>
</div>
<div class="hint">Enter to send • Shift+Enter for a new line • Say/type “create image …” for image generation</div>
</div></div>
</main>
<script>
const box=document.getElementById('box'),chat=document.getElementById('chat'),empty=document.getElementById('empty'),mic=document.getElementById('mic');
let history=JSON.parse(localStorage.getItem('sambot_history')||'[]');

function save(){localStorage.setItem('sambot_history',JSON.stringify(history.slice(-40)))}
function scroll(){chat.scrollTop=chat.scrollHeight}
function removeEmpty(){if(empty)empty.remove()}
function addMessage(text,role,extra){
 removeEmpty();
 const row=document.createElement('div');row.className='row '+role;
 const wrap=document.createElement('div');const msg=document.createElement('div');msg.className='msg';
 if(extra&&extra.image){const img=document.createElement('img');img.className='image-result';img.src=extra.image;msg.appendChild(img)}
 else msg.textContent=text;
 wrap.appendChild(msg);
 if(role==='assistant'&&!extra?.thinking){
   const actions=document.createElement('div');actions.className='message-actions';
   const copy=document.createElement('button');copy.className='mini';copy.textContent='Copy';copy.onclick=()=>navigator.clipboard?.writeText(text||'');
   actions.appendChild(copy);
   const speak=document.createElement('button');speak.className='mini';speak.textContent='🔊';speak.onclick=()=>speakText(text||'');
   actions.appendChild(speak);wrap.appendChild(actions);
 }
 row.appendChild(wrap);chat.appendChild(row);scroll();return msg
}
function restore(){history.forEach(m=>addMessage(m.content,m.role))}
function isImageRequest(s){return /\b(create|generate|make|draw|render)\s+(an?\s+)?image\b/i.test(s)||/^\/image\b/i.test(s)}
function cleanImagePrompt(s){return s.replace(/^\/image\s*/i,'').replace(/^\s*(create|generate|make|draw|render)\s+(an?\s+)?image\s*(of|showing)?\s*/i,'').trim()||s}
async function send(){
 const m=box.value.trim();if(!m)return;box.value='';
 if(isImageRequest(m)){await generateImage(cleanImagePrompt(m),m);return}
 history.push({role:'user',content:m});addMessage(m,'user');save();
 const thinking=addMessage('Thinking…','assistant',{thinking:true});thinking.classList.add('thinking');
 try{
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history.slice(-20)})});
  const j=await r.json();thinking.textContent=j.reply||j.error||'Something went wrong.';
  history.push({role:'assistant',content:thinking.textContent});save();
  const actions=document.createElement('div');actions.className='message-actions';
  const copy=document.createElement('button');copy.className='mini';copy.textContent='Copy';copy.onclick=()=>navigator.clipboard?.writeText(thinking.textContent);actions.appendChild(copy);
  const speak=document.createElement('button');speak.className='mini';speak.textContent='🔊';speak.onclick=()=>speakText(thinking.textContent);actions.appendChild(speak);
  thinking.parentElement.appendChild(actions);
 }catch(e){thinking.textContent='Connection error: '+e.message}
}
async function generateImage(prompt,shown){
 history.push({role:'user',content:shown});addMessage(shown,'user');save();
 const holder=addMessage('Creating your image… ⚡','assistant',{thinking:true});holder.classList.add('thinking');
 try{
  const r=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
  const j=await r.json();
  if(j.image){holder.textContent='';const img=document.createElement('img');img.className='image-result';img.src=j.image;holder.appendChild(img);history.push({role:'assistant',content:'[Generated image]'});save()}
  else holder.textContent=j.error||'Image generation failed.';
 }catch(e){holder.textContent='Image error: '+e.message}
}
function newChat(){history=[];localStorage.removeItem('sambot_history');chat.innerHTML='<div class="empty" id="empty"><h1>New chat</h1><p>Ask anything, or type <b>create image</b> to generate an image.</p></div>'}
function clearChat(){newChat()}
function toggleTheme(){document.body.classList.toggle('light');if(document.body.classList.contains('light')){document.body.style.background='#f7f7f8';document.body.style.color='#111'}else{document.body.style.background='#08090c';document.body.style.color='#f5f5f5'}}
function speakText(t){if('speechSynthesis' in window){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(t))}}
function voice(){
 if(!('webkitSpeechRecognition' in window||'SpeechRecognition' in window)){alert('Voice input is not supported in this browser.');return}
 const R=window.SpeechRecognition||window.webkitSpeechRecognition;const rec=new R();rec.lang='en-IN';rec.interimResults=false;mic.classList.add('active');mic.textContent='⏺ Listening…';
 rec.onresult=e=>{box.value=e.results[0][0].transcript;mic.classList.remove('active');mic.textContent='🎙 Voice';box.focus()}
 rec.onerror=()=>{mic.classList.remove('active');mic.textContent='🎙 Voice'}
 rec.onend=()=>{mic.classList.remove('active');mic.textContent='🎙 Voice'}
 rec.start()
}
box.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}})
if(history.length)restore();
</script>
</body>
</html>"""

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
