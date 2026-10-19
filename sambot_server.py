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
    memory: str | None = None
    instructions: str | None = None

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
        context = "\n\nCURRENT WEB RESULTS:\n" + "\n".join(
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
        system += "\n\nUSER-PROVIDED MEMORY (use only when relevant):\n" + memory
    if instructions:
        system += "\n\nUSER CUSTOM INSTRUCTIONS:\n" + instructions
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
                    yield "data: " + json.dumps({"token": piece}, ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"done": True, "model": model}) + "\n\n"
            print("SAMBOT_STREAM_OK: reply streamed")
        except Exception as exc:
            print(f"SAMBOT_STREAM_ERROR: {type(exc).__name__}: {exc}")
            yield "data: " + json.dumps({"error": f"AI stream failed ({type(exc).__name__}): {exc}"}) + "\n\n"
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
      if (url && (url.endsWith('/api/chat') || url.endsWith('/api/chat/stream')) && init && typeof init.body === 'string') {
        const body = JSON.parse(init.body);
        body.model = localStorage.getItem('sambot_model') || '';
        init = {...init, body: JSON.stringify(body)};
      }
    } catch (_) {}
    return nativeFetch(input, init);
  };

  // ChatGPT-style navigation and practical browser-side utilities.
  const sidebar = document.querySelector('#sidebar');
  const nav = document.createElement('div');
  nav.id = 'sambotExtraNav';
  nav.innerHTML = '<div class="history-title">WORKSPACE</div>'+
    '<button class="sidebtn" data-action="scheduled">◷ Scheduled</button>'+
    '<button class="sidebtn" data-action="library">▤ Library</button>'+
    '<button class="sidebtn" data-action="explore">✧ Explore tools</button>'+
    '<button class="sidebtn" data-action="plugins">◈ Plugins & tools</button>'+
    '<button class="sidebtn" data-action="codex">⌘ Coding workspace</button>';
  if(sidebar){const hist=sidebar.querySelector('.history-title');if(hist)hist.insertAdjacentElement('beforebegin',nav);else sidebar.prepend(nav);}
  const style=document.createElement('style');
  style.textContent=`
    #sambotExtraNav{padding:5px 0 8px;border-bottom:1px solid #252831;margin-bottom:7px}
    #sambotExtraNav .sidebtn{padding:8px;font-size:13px}
    .sambot-ui-modal{position:fixed;inset:0;z-index:9999;background:#000a;display:none;align-items:center;justify-content:center;padding:18px}
    .sambot-ui-modal.open{display:flex}
    .sambot-ui-card{width:min(560px,100%);max-height:82vh;overflow:auto;background:#171a20;color:#f5f5f5;border:1px solid #343842;border-radius:16px;padding:20px}
    .sambot-ui-card h2{margin:0 0 10px}.sambot-ui-card p{color:#aeb3bd;font-size:13px;line-height:1.5}
    .sambot-ui-card button,.sambot-ui-card input,.sambot-ui-card textarea,.sambot-ui-card select{font:inherit}
    .sambot-ui-card button{background:#252a33;color:inherit;border:1px solid #414754;border-radius:9px;padding:9px 11px;margin:4px;cursor:pointer}
    .sambot-ui-card input,.sambot-ui-card textarea{display:block;width:100%;margin:8px 0;padding:10px;border-radius:8px;border:1px solid #414754;background:#0e1014;color:inherit}
    .sambot-ui-item{padding:10px;border:1px solid #343842;border-radius:9px;margin:7px 0;overflow-wrap:anywhere}
    @media print{body{height:auto;overflow:visible;background:white;color:black}.sidebar,.topbar,.composer,.actions,.sambot-ui-modal{display:none!important}.app,.main,.chat{height:auto;display:block;overflow:visible;background:white;color:black;padding:0}.msg,.user .msg{background:white!important;color:black!important;border:1px solid #ddd;break-inside:avoid}.row{break-inside:avoid}}
    .light #sambotExtraNav{border-color:#ddd}.light .sambot-ui-card{background:white;color:#111}.light .sambot-ui-card input,.light .sambot-ui-card textarea{background:white;color:#111}
  `;
  document.head.appendChild(style);
  const ui=document.createElement('div');ui.className='sambot-ui-modal';ui.id='sambotUiModal';
  ui.innerHTML='<div class="sambot-ui-card"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><h2 id="sambotUiTitle">Sambot</h2><button id="sambotUiClose">✕ Close</button></div><div id="sambotUiBody"></div></div>';
  document.body.appendChild(ui);
  const uiTitle=ui.querySelector('#sambotUiTitle'),uiBody=ui.querySelector('#sambotUiBody');
  const closeUi=()=>ui.classList.remove('open');
  ui.querySelector('#sambotUiClose').onclick=closeUi;ui.addEventListener('click',e=>{if(e.target===ui)closeUi()});
  function showUi(title,html){uiTitle.textContent=title;uiBody.innerHTML=html;ui.classList.add('open')}
  function addPrompt(text){const b=document.querySelector('#box');if(b){b.value=text;b.focus();closeUi();}}
  function libraryView(){
    const items=JSON.parse(localStorage.getItem('sambot_library')||'[]');
    showUi('Library','<p>Save useful answers here on this device. Nothing is uploaded to an account.</p><button id="saveCurrent">＋ Save current conversation</button><div id="libraryItems"></div>');
    uiBody.querySelector('#saveCurrent').onclick=()=>{
      const sessions=JSON.parse(localStorage.getItem('sambot_sessions')||'[]'),id=localStorage.getItem('sambot_current');
      const s=sessions.find(x=>String(x.id)===String(id));if(!s||!s.messages?.length){alert('Start a conversation first.');return;}
      const lib=JSON.parse(localStorage.getItem('sambot_library')||'[]');lib.unshift({title:s.title||'Saved conversation',savedAt:new Date().toISOString(),messages:s.messages});localStorage.setItem('sambot_library',JSON.stringify(lib.slice(0,100)));libraryView();
    };
    const box=uiBody.querySelector('#libraryItems');
    (items||[]).forEach((it,i)=>{const d=document.createElement('div');d.className='sambot-ui-item';const title=document.createElement('b');title.textContent=it.title||'Saved conversation';const open=document.createElement('button');open.textContent='Use as prompt';open.onclick=()=>addPrompt((it.messages||[]).map(m=>(m.role||'')+': '+(m.content||'')).join('\n\n'));const del=document.createElement('button');del.textContent='Delete';del.onclick=()=>{const a=JSON.parse(localStorage.getItem('sambot_library')||'[]');a.splice(i,1);localStorage.setItem('sambot_library',JSON.stringify(a));libraryView()};d.append(title,open,del);box.appendChild(d)});
    if(!items.length)box.innerHTML='<p>Your saved items will appear here.</p>';
  }
  function scheduledView(){
    const read=()=>JSON.parse(localStorage.getItem('sambot_reminders')||'[]');
    showUi('Scheduled reminders','<p>Create a reminder stored in this browser. Keep Sambot open for on-time alerts; browser notifications may require permission.</p><input id="reminderText" placeholder="What should I remind you about?"><label>Date and time</label><input id="reminderTime" type="datetime-local"><button id="addReminder">＋ Schedule reminder</button><div id="reminderItems"></div>');
    uiBody.querySelector('#addReminder').onclick=()=>{const text=uiBody.querySelector('#reminderText').value.trim(),when=new Date(uiBody.querySelector('#reminderTime').value).getTime();if(!text||!Number.isFinite(when)||when<=Date.now()){alert('Enter a reminder and a future date/time.');return;}const a=read();a.push({id:Date.now(),text,when,done:false});localStorage.setItem('sambot_reminders',JSON.stringify(a));scheduledView();};
    const list=uiBody.querySelector('#reminderItems');read().forEach((r,i)=>{const d=document.createElement('div');d.className='sambot-ui-item';d.textContent=r.done?'✓ '+r.text:r.text+' — '+new Date(r.when).toLocaleString();if(!r.done){const del=document.createElement('button');del.textContent='Delete';del.onclick=()=>{const a=read();a.splice(i,1);localStorage.setItem('sambot_reminders',JSON.stringify(a));scheduledView()};d.appendChild(del)}list.appendChild(d)});
  }
  function checkReminders(){try{const a=JSON.parse(localStorage.getItem('sambot_reminders')||'[]');let changed=false;a.forEach(r=>{if(!r.done&&r.when<=Date.now()){alert('Sambot reminder: '+r.text);r.done=true;changed=true;}});if(changed)localStorage.setItem('sambot_reminders',JSON.stringify(a));}catch(_){}}
  checkReminders();setInterval(checkReminders,30000);
  const toolContent={
    explore:[['Write','Help me write a clear, polished piece of writing.'],['Learn','Teach me this topic step by step with examples.'],['Plan','Create a practical plan with milestones and a checklist.'],['Brainstorm','Give me creative ideas, compare them, and recommend one.'],['Study quiz','Quiz me one question at a time and explain my mistakes.']],
    plugins:[['Web research','Research this topic using current web information and cite useful sources.'],['Analyze data','Help me analyze the data I attach; explain the method and limitations.'],['Image prompt','Help me create a detailed image-generation prompt.'],['Calculator','Open the calculator from the Sambot sidebar.']],
    codex:[['Explain code','Explain the code I paste, line by line, with examples.'],['Debug code','Debug this code. Identify the root cause, then provide a corrected version and tests.'],['Build a project','Help me build a complete project with a file tree, code, setup instructions, and tests.'],['Review code','Review this code for bugs, security issues, and performance problems.']]
  };
  function toolView(kind){
    const names={explore:'Explore',plugins:'Plugins & tools',codex:'Coding workspace'};
    showUi(names[kind],'<p>Choose a workflow to start it in the chat. These are built-in prompt shortcuts, not external plugins.</p><div id="sambotWorkflowList"></div>');
    const list=uiBody.querySelector('#sambotWorkflowList');
    toolContent[kind].forEach(([label,prompt])=>{const d=document.createElement('div');d.className='sambot-ui-item';const b=document.createElement('button');b.textContent=label;b.onclick=()=>{if(label==='Calculator'){closeUi();const c=document.querySelector('.sidebtn[onclick="openCalculator()"]');if(c)c.click();else alert('Use the Calculator button in the sidebar.');return;}addPrompt(prompt)};d.appendChild(b);list.appendChild(d)});
  }
  nav.addEventListener('click',e=>{const b=e.target.closest('button[data-action]');if(!b)return;const a=b.dataset.action;if(a==='scheduled')scheduledView();else if(a==='library')libraryView();else toolView(a)});
  const topActions=document.querySelector('.top-actions');
  if(topActions){const pdf=document.createElement('button');pdf.className='iconbtn';pdf.textContent='⤓ Export PDF';pdf.title='Print or save the current chat as PDF';pdf.onclick=()=>window.print();topActions.appendChild(pdf);}

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
