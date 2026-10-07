import os
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="SAMBOT X")

class ChatRequest(BaseModel):
    message: str

class ImageRequest(BaseModel):
    prompt: str

HTML = r"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAMBOT X</title>
<style>body{margin:0;font-family:Inter,system-ui;background:#0b0b0f;color:#f5f5f5}main{max-width:900px;margin:auto;height:100vh;display:flex;flex-direction:column}header{padding:20px 24px;font-size:22px;font-weight:700;border-bottom:1px solid #222}.tag{opacity:.55;font-size:12px;margin-left:8px}.chat{flex:1;overflow:auto;padding:24px}.msg{max-width:78%;padding:14px 16px;border-radius:16px;margin:12px 0;white-space:pre-wrap;line-height:1.45}.u{margin-left:auto;background:#2b2f3a}.a{background:#15171d}.bar{display:flex;gap:10px;padding:18px;border-top:1px solid #222}.bar textarea{flex:1;resize:none;background:#15171d;color:white;border:1px solid #2a2d36;border-radius:14px;padding:13px;font-size:15px}.bar button{border:0;border-radius:14px;padding:0 20px;background:#fff;color:#000;font-weight:700;cursor:pointer}.hint{text-align:center;opacity:.45;font-size:12px;padding-bottom:12px} .image{background:#7c5cff;color:white}</style></head>
<body><main><header>✨ SAMBOT X <span class="tag">Groq-powered</span></header><section id="chat" class="chat"><div class="msg a">Hey! I'm Sambot X. Ask me anything.</div></section><div class="hint">Your GROQ_API_KEY stays on the server.</div><div class="bar"><textarea id="box" rows="2" placeholder="Message Sambot X..."></textarea><button onclick="send()">Send</button><button class="image" onclick="image()">🎨 Create Image</button></div></main>
<script>const box=document.getElementById('box'),chat=document.getElementById('chat');function add(t,c){const d=document.createElement('div');d.className='msg '+c;d.textContent=t;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}async function send(){const m=box.value.trim();if(!m)return;box.value='';add(m,'u');const a=add('Thinking…','a');try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});const j=await r.json();a.textContent=j.reply||j.error||'Something went wrong.'}catch(e){a.textContent='Server error. Check your Render logs.'}}async function image(){const m=box.value.trim();if(!m)return;box.value='';add('🎨 '+m,'u');const a=add('Creating your image… ⚡','a');try{const r=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:m})});const j=await r.json();if(j.image){a.textContent='';const img=document.createElement('img');img.style.maxWidth='100%';img.style.borderRadius='14px';img.src=j.image;a.appendChild(img)}else a.textContent=j.error||'Image generation failed.'}catch(e){a.textContent='Image server error. Check your Render logs.'}}
box.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}})</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/health")
def health():
    return {"ok": True, "groq_configured": bool(os.getenv("GROQ_API_KEY"))}

@app.post("/api/image")
def image(req: ImageRequest):
    account=os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token=os.getenv("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        return {"error":"Cloudflare image generation is not configured in Render."}
    url=f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    try:
        r=requests.post(url,headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},json={"prompt":req.prompt,"steps":4},timeout=90)
        r.raise_for_status()
        image_b64=r.json()["result"]["image"]
        return {"image":f"data:image/jpeg;base64,{image_b64}"}
    except Exception as e:
        return {"error":f"Cloudflare image generation failed: {e}"}

@app.post("/api/chat")
def chat(req: ChatRequest):
    key=os.getenv("GROQ_API_KEY")
    if not key:
        return {"error":"GROQ_API_KEY is not configured in Render."}
    client=Groq(api_key=key)
    r=client.chat.completions.create(
        model=os.getenv("GROQ_MODEL","llama-3.3-70b-versatile"),
        messages=[
            {"role":"system","content":"You are Sambot X, a helpful, smart, concise AI assistant. Be friendly and accurate."},
            {"role":"user","content":req.message}
        ],
        temperature=0.7,
        max_tokens=700,
    )
    return {"reply": r.choices[0].message.content}
