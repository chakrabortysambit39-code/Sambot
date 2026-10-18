"""Render entry point for Sambot X, including optional feature routes."""
import os
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from groq import Groq
import web_app
from web_app import app
from sambot_features import router as features_router, CHAT_MODELS

app.router.routes[:] = [
    route for route in app.router.routes
    if not (getattr(route, "path", None) == "/api/chat" and "POST" in getattr(route, "methods", set()))
]

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    web_search: bool = False
    model: str | None = None

@app.post("/api/chat/stream")
def stream_chat(req: ChatRequest):
    """Stream assistant text as Server-Sent Events for the browser chat UI."""
    import json
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return JSONResponse({"error": "GROQ_API_KEY is not configured in Render."}, status_code=503)
    allowed = {m["id"] for m in CHAT_MODELS}
    model = req.model if req.model in allowed else os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    messages = [{"role": m.role, "content": m.content} for m in req.messages if m.role in ("user", "assistant")][-20:]
    if not messages:
        return JSONResponse({"error": "No chat messages were sent."}, status_code=400)
    context = ""
    if req.web_search:
        results = web_app.web_search(messages[-1]["content"])
        context = "\\n\\nCURRENT WEB RESULTS:\\n" + "\\n".join(
            f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results
        )
    memory = (req.memory or "").strip()[:4000]
    instructions = (req.instructions or "").strip()[:4000]
    system = (
        "You are Sambot X, a helpful AI assistant. Be accurate, clear, and honest about limitations. "
        "Help with coding, writing, studying, math, planning, brainstorming, and general tasks. "
        "Use attached file contents when supplied. If web results are supplied, use them for current information and mention sources naturally. "
        "Format answers clearly with Markdown when useful. Never claim to have used tools or sources you did not use."
    )
    if memory:
        system += "\\n\\nUSER-PROVIDED MEMORY (use only when relevant):\\n" + memory
    if instructions:
        system += "\\n\\nUSER CUSTOM INSTRUCTIONS:\\n" + instructions
    def events():
        try:
            stream = Groq(api_key=key, timeout=90.0, max_retries=1).chat.completions.create(
                model=model, messages=[{"role": "system", "content": system + context}] + messages,
                temperature=0.7, max_tokens=4000, stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None)
                if piece:
                    yield "data: " + json.dumps({"token": piece}, ensure_ascii=False) + "\\n\\n"
            yield "data: " + json.dumps({"done": True, "model": model}) + "\\n\\n"
            print("SAMBOT_STREAM_OK: reply streamed")
        except Exception as exc:
            print(f"SAMBOT_STREAM_ERROR: {type(exc).__name__}: {exc}")
            yield "data: " + json.dumps({"error": f"AI stream failed ({type(exc).__name__}): {exc"}) + "\\n\\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"
    })

@app.post("/api/chat")
def selected_model_chat(req: ChatRequest):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return JSONResponse({"error": "GROQ_API_KEY is not configured in Render."}, status_code=503)
    allowed = {m["id"] for m in CHAT_MODELS}
    model = req.model if req.model in allowed else os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    try:
        messages = [{"role": m.role, "content": m.content} for m in req.messages if m.role in ("user", "assistant")][-20:]
        if not messages:
            return JSONResponse({"error": "No chat messages were sent."}, status_code=400)
        context = ""
        if req.web_search:
            results = web_app.web_search(messages[-1]["content"])
            context = "\n\nCURRENT WEB RESULTS:\n" + "\n".join(
                f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results
            )
        system = (
            "You are Sambot X, a helpful AI assistant. Be accurate, clear, and honest about limitations. "
            "Help with coding, writing, studying, math, planning, brainstorming, and general tasks. "
            "Use attached file contents when supplied. If web results are supplied, use them for current information and mention sources naturally."
        )
        result = Groq(api_key=key, timeout=45.0, max_retries=1).chat.completions.create(
            model=model, messages=[{"role": "system", "content": system + context}] + messages,
            temperature=0.7, max_tokens=1800,
        )
        reply = result.choices[0].message.content
        if not reply:
            return JSONResponse({"error": "The AI returned an empty reply. Please try again."}, status_code=502)
        return {"reply": reply, "model": model}
    except Exception as exc:
        print(f"SAMBOT_CHAT_ERROR: {type(exc).__name__}: {exc}")
        return JSONResponse({"error": f"AI request failed ({type(exc).__name__}): {exc}"}, status_code=502)

app.include_router(features_router)

_original_home = next((r.endpoint for r in app.router.routes if getattr(r, "path", None) == "/" and "GET" in getattr(r, "methods", set())), None)
if _original_home:
    def enhanced_home():
        original = _original_home()
        html = original.body.decode("utf-8") if hasattr(original, "body") else str(original)
        extension = r"""
<script>
(function(){
  if (window.__sambotEnhancementsLoaded) return;
  window.__sambotEnhancementsLoaded = true;
  const nativeFetch = window.fetch.bind(window);
  window.fetch = function(input, init){
    try {
      const url = typeof input === 'string' ? input : input.url;
      if (url && url.endsWith('/api/chat') && init && typeof init.body === 'string') {
        const body = JSON.parse(init.body);
        body.model = localStorage.getItem('sambot_model') || '';
        init = {...init, body: JSON.stringify(body)};
      }
    } catch (_) {}
    return nativeFetch(input, init);
  };
  const topbar = document.querySelector('.topbar > div:first-child');
  if (topbar) {
    const select = document.createElement('select');
    select.id = 'sambotModelPicker'; select.title = 'Choose the chat model';
    select.setAttribute('aria-label','Choose AI model');
    select.style.cssText = 'margin-left:10px;max-width:190px;background:#15181e;color:inherit;border:1px solid #343842;border-radius:8px;padding:7px;font-size:12px';
    select.innerHTML = '<option>Loading models…</option>'; topbar.appendChild(select);
    nativeFetch('/api/models').then(r=>r.json()).then(data=>{
      select.innerHTML = '';
      (data.models||[]).forEach(m=>{const o=document.createElement('option');o.value=m.id;o.textContent=m.name;select.appendChild(o)});
      select.value=localStorage.getItem('sambot_model')||data.default;
      if(!select.value && select.options.length)select.selectedIndex=0;
      localStorage.setItem('sambot_model',select.value);
    }).catch(()=>{select.innerHTML='<option value="openai/gpt-oss-120b">Default model</option>'});
    select.addEventListener('change',()=>localStorage.setItem('sambot_model',select.value));
  }
  const tools = document.querySelector('.composer .tools');
  if (tools) {
    const imageBtn = document.createElement('button'); imageBtn.className='toolbtn'; imageBtn.textContent='🖼 Analyze image';
    const imageInput=document.createElement('input');imageInput.type='file';imageInput.accept='image/png,image/jpeg,image/webp,image/gif';imageInput.hidden=true;
    imageBtn.onclick=()=>imageInput.click();
    imageInput.onchange=async()=>{
      const file=imageInput.files && imageInput.files[0];if(!file)return;
      if(file.size>8*1024*1024){alert('Choose an image under 8 MB.');imageInput.value='';return;}
      const prompt=window.prompt('What should Sambot look for in this image?','Describe this image and explain anything important.');
      if(prompt===null){imageInput.value='';return;}
      const reader=new FileReader();
      reader.onload=async()=>{
        try{
          if(typeof window.add==='function')window.add('user','🖼 Image: '+file.name);
          if(typeof window.add==='function')window.add('assistant','Analyzing image…');
          const r=await nativeFetch('/api/vision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,image_data_url:reader.result})});
          const j=await r.json();
          const rows=document.querySelectorAll('#chat .row.assistant');const last=rows[rows.length-1];
          if(last && last.textContent.includes('Analyzing image'))last.remove();
          if(typeof window.add==='function')window.add('assistant',r.ok?(j.reply||'No response returned.'):('Image analysis error: '+(j.error||r.status)));
        }catch(e){alert('Image analysis failed: '+e.message)}
      };
      reader.readAsDataURL(file);imageInput.value='';
    };
    tools.appendChild(imageBtn);tools.appendChild(imageInput);
  }
})();
</script>
"""
        html = html.replace('</body>', extension + '</body>')
        return HTMLResponse(html)
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) != "/"]
    app.add_api_route("/", enhanced_home, methods=["GET"], response_class=HTMLResponse)
