"""Render entry point for Sambot X, including optional feature routes."""
import os
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi import Header, Request
from pydantic import BaseModel
from groq import Groq
import web_app
from web_app import app
from sambot_features import router as features_router, CHAT_MODELS
from billing import router as billing_router, record_usage

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
def stream_chat(req: ChatRequest, request: Request, authorization: str | None = Header(default=None)):
    """Stream assistant text as Server-Sent Events for the browser chat UI."""
    import json
    record_usage(authorization, request.client.host if request and request.client else 'unknown')
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
def selected_model_chat(req: ChatRequest, request: Request, authorization: str | None = Header(default=None)):
    record_usage(authorization)
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
app.include_router(billing_router)

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

  // Direct UPI Premium payments; the owner manually verifies each submitted UTR.
  const billingButton=document.createElement('button');billingButton.className='iconbtn';billingButton.textContent='✦ Premium';billingButton.onclick=openBilling;
  const billingCss=document.createElement('style');billingCss.textContent='.sambot-billing-card{background:#171a20;color:#f5f5f5;border:1px solid #343842;border-radius:17px;padding:22px;width:min(560px,100%);max-height:85vh;overflow:auto;box-shadow:0 24px 90px #0009}.sambot-billing-card input,.sambot-billing-card textarea{width:100%;margin:7px 0 12px;padding:11px;border:1px solid #414754;border-radius:9px;background:#0e1014;color:inherit}.sambot-billing-card button{padding:10px 13px;margin:4px 4px 4px 0;border:1px solid #414754;border-radius:9px;background:#242a35;color:inherit;cursor:pointer}.sambot-billing-card button.primary{background:#f4f5f7;color:#111;border-color:#f4f5f7;font-weight:700}.sambot-plan{border:1px solid #3d4555;border-radius:13px;padding:15px;margin:12px 0;background:linear-gradient(135deg,#202634,#15181f)}.sambot-billing-muted{font-size:12px;color:#aeb5c2;line-height:1.55}.sambot-billing-status{font-size:13px;color:#a8c5ff;min-height:20px;margin:8px 0}.sambot-upi-qr{display:block;width:220px;height:220px;max-width:100%;margin:12px auto;background:white;padding:8px;border-radius:10px}.sambot-admin-request{padding:12px;border:1px solid #3d4555;border-radius:10px;margin:9px 0;overflow-wrap:anywhere}.light .sambot-billing-card{background:white;color:#111}.light .sambot-billing-card input,.light .sambot-billing-card textarea{background:white;color:#111}';document.head.appendChild(billingCss);
  const billingOverlay=document.createElement('div');billingOverlay.className='sambot-ui-modal';billingOverlay.id='sambotBillingOverlay';
  billingOverlay.innerHTML='<div class="sambot-billing-card"><div style="display:flex;justify-content:space-between;align-items:center"><h2 style="margin:0">Sambot Premium</h2><button id="billingClose">✕</button></div><p class="sambot-billing-muted">₹299 · 30 days · Direct UPI · Manual approval</p><div id="billingContent">Loading billing…</div><div id="billingStatus" class="sambot-billing-status" aria-live="polite"></div></div>';
  document.body.appendChild(billingOverlay);
  const billingContent=billingOverlay.querySelector('#billingContent'),billingStatus=billingOverlay.querySelector('#billingStatus');
  const getBillingToken=()=>localStorage.getItem('sambot_billing_token')||'';
  const billingFetch=(url,options={})=>nativeFetch(url,{...options,headers:{...(options.headers||{}),...(getBillingToken()?{Authorization:'Bearer '+getBillingToken()}:{}),'Content-Type':'application/json'}});
  function billingMessage(t){billingStatus.textContent=t}
  function openBilling(){billingOverlay.classList.add('open');renderBilling()}
  billingOverlay.querySelector('#billingClose').onclick=()=>billingOverlay.classList.remove('open');
  billingOverlay.addEventListener('click',e=>{if(e.target===billingOverlay)billingOverlay.classList.remove('open')});
  async function billingJson(url,options){const r=await billingFetch(url,options);const j=await r.json();if(!r.ok)throw Error(j.detail||j.error||'Request failed');return j}
  async function renderBilling(){
    const token=getBillingToken();
    if(!token){
      billingContent.innerHTML='<div class="sambot-plan"><h3>✦ Premium · ₹299 for 30 days</h3><p class="sambot-billing-muted">Free: 30 AI messages/month. Premium: up to 1,000/month. Sign in by email code; no password.</p></div><label>Email address</label><input id="billingEmail" type="email" placeholder="you@example.com" autocomplete="email"><button class="primary" id="billingSendCode">Send sign-in code</button><div id="billingCodeArea"></div>';
      billingContent.querySelector('#billingSendCode').onclick=async()=>{const email=billingContent.querySelector('#billingEmail').value.trim();if(!email){billingMessage('Enter your email address.');return}try{await billingJson('/api/billing/request-code',{method:'POST',body:JSON.stringify({email})});billingMessage('Code sent. Check your email.');const area=billingContent.querySelector('#billingCodeArea');area.innerHTML='<input id="billingCode" inputmode="numeric" maxlength="6" placeholder="6-digit code"><button class="primary" id="billingVerifyCode">Verify and sign in</button>';area.querySelector('#billingVerifyCode').onclick=async()=>{try{const result=await billingJson('/api/billing/verify-code',{method:'POST',body:JSON.stringify({email,code:area.querySelector('#billingCode').value.trim()})});localStorage.setItem('sambot_billing_token',result.token);billingMessage('Signed in.');renderBilling()}catch(e){billingMessage(e.message)}}}catch(e){billingMessage(e.message)}};
      return;
    }
    try{
      const [status,requests,config]=await Promise.all([billingJson('/api/billing/status'),billingJson('/api/billing/requests'),billingJson('/api/billing/config')]);
      const expiry=status.current_period_end?new Date(status.current_period_end*1000).toLocaleString():'—';
      billingContent.innerHTML='<div class="sambot-plan"><h3>Plan: '+(status.plan==='premium'?'✦ Premium':'Free')+'</h3><p class="sambot-billing-muted">Signed in as '+status.email+'</p><p class="sambot-billing-muted">Chat usage this month: '+status.usage+' / '+(status.plan==='premium'?1000:30)+'</p><p class="sambot-billing-muted">Premium expiry: '+(status.plan==='premium'?expiry:'Not active')+'</p></div><div id="billingPayArea"></div><h3>My payment requests</h3><div id="billingMyRequests"></div>'+(status.is_owner?'<hr><h3>👑 Owner dashboard</h3><div id="billingOwnerPanel">Loading owner requests…</div>':'')+'<button id="billingSignOut">Sign out</button>';
      const pay=billingContent.querySelector('#billingPayArea');
      if(status.plan!=='premium'){
        const upiUri='upi://pay?pa='+encodeURIComponent(config.upi_id)+'&pn='+encodeURIComponent(config.payee_name)+'&am=299.00&cu=INR&tn='+encodeURIComponent('Sambot X Premium 30 days');
        pay.innerHTML='<div class="sambot-plan"><h3>Pay directly by UPI</h3><p class="sambot-billing-muted">Pay ₹299 to <b>'+config.upi_id+'</b>. Check the payee name in your UPI app before paying. After payment, submit the transaction reference/UTR below. Premium activates only after the owner checks their UPI app and approves it.</p><img class="sambot-upi-qr" alt="UPI payment QR code" src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data='+encodeURIComponent(upiUri)+'"><button id="billingOpenUpi" class="primary">Open UPI app</button><button id="billingCopyUpi">Copy UPI ID</button><label>UPI transaction reference / UTR</label><input id="billingUtr" maxlength="100" placeholder="Enter transaction reference"><button id="billingSubmitUtr" class="primary">Submit payment for review</button><p class="sambot-billing-muted">This does not automatically verify payment. Never enter your UPI PIN or OTP here.</p></div>';
        pay.querySelector('#billingOpenUpi').onclick=()=>{window.location.href=upiUri};
        pay.querySelector('#billingCopyUpi').onclick=async()=>{try{await navigator.clipboard.writeText(config.upi_id);billingMessage('UPI ID copied.')}catch(_){billingMessage('UPI ID: '+config.upi_id)}};
        pay.querySelector('#billingSubmitUtr').onclick=async()=>{const reference=pay.querySelector('#billingUtr').value.trim();if(!reference){billingMessage('Enter the UPI transaction reference.');return}try{await billingJson('/api/billing/submit-upi',{method:'POST',body:JSON.stringify({reference,amount_rupees:299})});billingMessage('Submitted. Your payment is waiting for owner review.');renderBilling()}catch(e){billingMessage(e.message)}};
      }else{pay.innerHTML='<p class="sambot-billing-muted">Premium is active. Pay again after expiry to extend access.</p>'}
      const my=billingContent.querySelector('#billingMyRequests');
      if(!requests.requests.length)my.innerHTML='<p class="sambot-billing-muted">No payment requests yet.</p>';
      requests.requests.forEach(item=>{const d=document.createElement('div');d.className='sambot-admin-request';d.textContent='₹'+(item.amount/100)+' · Ref '+item.reference+' · '+item.status+(item.review_note?' · '+item.review_note:'');my.appendChild(d)});
      if(status.is_owner)await renderOwnerDashboard();
      billingContent.querySelector('#billingSignOut').onclick=()=>{localStorage.removeItem('sambot_billing_token');billingMessage('Signed out.');renderBilling()};
    }catch(e){billingContent.innerHTML='<p class="sambot-billing-muted">Could not load billing status: '+e.message+'</p><button id="billingRetry">Retry</button><button id="billingSignOut">Sign out</button>';billingContent.querySelector('#billingRetry').onclick=renderBilling;billingContent.querySelector('#billingSignOut').onclick=()=>{localStorage.removeItem('sambot_billing_token');renderBilling()}}
  }
  async function renderOwnerDashboard(){
    const panel=billingContent.querySelector('#billingOwnerPanel');if(!panel)return;
    try{
      const result=await billingJson('/api/billing/owner/requests');panel.innerHTML='';
      const pending=result.requests.filter(x=>x.status==='pending');
      if(!pending.length)panel.innerHTML='<p class="sambot-billing-muted">No pending payment requests.</p>';
      pending.forEach(item=>{const d=document.createElement('div');d.className='sambot-admin-request';const info=document.createElement('p');info.textContent=item.email+' · ₹'+(item.amount/100)+' · UTR '+item.reference;const approve=document.createElement('button');approve.className='primary';approve.textContent='Approve 30 days';approve.onclick=()=>reviewOwnerRequest(item.id,'approve');const reject=document.createElement('button');reject.textContent='Reject';reject.onclick=()=>reviewOwnerRequest(item.id,'reject');d.append(info,approve,reject);panel.appendChild(d)});
    }catch(e){panel.textContent='Owner dashboard: '+e.message}
  }
  async function reviewOwnerRequest(id,decision){const note=decision==='reject'?(window.prompt('Reason for rejection (optional):')||''):'';try{await billingJson('/api/billing/owner/review',{method:'POST',body:JSON.stringify({request_id:id,decision,note})});billingMessage(decision==='approve'?'Approved. Premium activated for 30 days.':'Payment request rejected.');renderBilling()}catch(e){billingMessage(e.message)}}
  const priorFetchForBilling=window.fetch.bind(window);
  window.fetch=(input,init={})=>{const url=typeof input==='string'?input:(input&&input.url)||'';if((url.endsWith('/api/chat')||url.endsWith('/api/chat/stream'))&&getBillingToken()){const headers=new Headers(init.headers||(input instanceof Request?input.headers:undefined));headers.set('Authorization','Bearer '+getBillingToken());init={...init,headers};}return priorFetchForBilling(input,init)};
  const topActions=document.querySelector('.top-actions');
  if(topActions){topActions.prepend(billingButton);const pdf=document.createElement('button');pdf.className='iconbtn';pdf.textContent='⤓ Export PDF';pdf.title='Print or save the current chat as PDF';pdf.onclick=()=>window.print();topActions.appendChild(pdf);}


  // Premium visual layer: responsive layout, welcome actions, and command palette.
  const premiumStyle=document.createElement('style');
  premiumStyle.textContent=`
    :root{color-scheme:dark}
    body{background:radial-gradient(ellipse at 52% -20%,#202b42 0%,#0b0d12 48%,#08090c 78%)!important}
    .sidebar{background:rgba(12,14,19,.94)!important;backdrop-filter:blur(18px);border-right-color:#292d38!important}
    .brand{letter-spacing:.2px;padding:13px 10px 17px!important;font-size:20px!important}
    .brand:after{content:'  •';color:#78a9ff;font-size:12px}
    .new{background:linear-gradient(135deg,#222834,#171a21)!important;border-color:#41495a!important;transition:transform .16s,border-color .16s}
    .new:hover,.sidebtn:hover,.toolbtn:hover,.iconbtn:hover{border-color:#66738b!important;transform:translateY(-1px)}
    .sidebtn,.chatitem,.toolbtn,.iconbtn{transition:background .16s,border-color .16s,transform .16s}
    .topbar{background:rgba(8,9,12,.72);backdrop-filter:blur(16px);border-bottom-color:#272b34!important}
    .model{letter-spacing:.2px}
    .status{padding:4px 7px;border:1px solid #2c3441;border-radius:99px;color:#9db4d7;opacity:1!important}
    .chat{scroll-behavior:smooth;padding-top:30px!important}
    .empty{max-width:800px!important;margin:clamp(45px,12vh,120px) auto!important;padding:0 10px}
    .empty h1{font-size:clamp(30px,4vw,46px)!important;letter-spacing:-1.5px;background:linear-gradient(100deg,#fff 15%,#b8c9ed 65%,#8fa8d5);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:13px!important}
    .empty p{font-size:15px;line-height:1.7;opacity:.68!important}
    .sambot-greeting{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:30px auto 0;max-width:690px;text-align:left}
    .sambot-prompt-card{border:1px solid #303746;background:linear-gradient(135deg,rgba(28,33,44,.88),rgba(17,20,27,.9));color:#f3f5fa;border-radius:15px;padding:15px;min-height:88px;cursor:pointer;display:flex;flex-direction:column;gap:7px;transition:transform .16s,border-color .16s,background .16s}
    .sambot-prompt-card:hover{transform:translateY(-2px);border-color:#7183a3;background:#252c3a}
    .sambot-prompt-card b{font-size:13px}.sambot-prompt-card span{font-size:12px;color:#aab3c3;line-height:1.45}
    .composer{background:linear-gradient(transparent,rgba(8,9,12,.96) 25%)!important}
    .compose{border-radius:22px!important;background:rgba(22,25,32,.96)!important;border-color:#3b414f!important;box-shadow:0 15px 50px #0007,0 0 0 1px #ffffff04!important;backdrop-filter:blur(18px)}
    .compose:focus-within{border-color:#65748e!important;box-shadow:0 15px 50px #0008,0 0 0 3px #7895c51a!important}
    .compose textarea{font-size:15px!important;line-height:1.55}
    .send{background:#f4f5f7!important;color:#111!important;border-radius:10px!important}
    .msg{border:1px solid #ffffff08;box-shadow:0 2px 8px #0001}
    .assistant .msg{background:rgba(18,21,28,.88)!important}
    .user .msg{background:#292e39!important;border-color:#414858}
    .row{animation:sambotFadeIn .2s ease-out}
    @keyframes sambotFadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
    .mini{transition:all .15s}.mini:hover{color:#fff;border-color:#596273}
    #sambotCommandOverlay{position:fixed;inset:0;background:#000b;backdrop-filter:blur(8px);z-index:10010;display:none;align-items:flex-start;justify-content:center;padding:14vh 16px 20px}
    #sambotCommandOverlay.open{display:flex}
    #sambotCommandBox{width:min(600px,100%);background:#171a21;border:1px solid #424958;border-radius:17px;box-shadow:0 30px 100px #000a;overflow:hidden}
    #sambotCommandInput{width:100%;padding:17px 18px;background:transparent;border:0;border-bottom:1px solid #303541;color:#fff;outline:none;font-size:15px}
    #sambotCommandResults{padding:8px;max-height:48vh;overflow:auto}
    .sambot-command-item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px;border-radius:10px;cursor:pointer;color:#eee;font-size:13px}
    .sambot-command-item:hover,.sambot-command-item.active{background:#2a303c}
    .sambot-command-item small{color:#9da5b4}
    #sambotCommandHint{padding:9px 13px;border-top:1px solid #303541;color:#8e96a5;font-size:11px}
    .sambot-shortcut{font-size:10px;color:#aab2c0;border:1px solid #424958;border-radius:5px;padding:2px 5px}
    .light{background:#f7f8fb!important;color:#16181d!important}
    .light .sidebar{background:rgba(249,250,252,.95)!important}
    .light .topbar{background:rgba(255,255,255,.85)!important}
    .light .empty h1{background:linear-gradient(100deg,#202633,#536a91);-webkit-background-clip:text;background-clip:text}
    .light .sambot-prompt-card{background:#fff;color:#17191e;border-color:#e0e3e9}
    .light .sambot-prompt-card span{color:#626b7a}
    .light .compose{background:#fff!important;border-color:#d9dde5!important}
    .light .assistant .msg{background:#fff!important;color:#17191e;border-color:#e5e7eb}
    .light #sambotCommandBox{background:#fff;color:#111;border-color:#ddd}
    .light #sambotCommandInput{color:#111}
    .light .sambot-command-item{color:#111}
    @media(max-width:760px){.sambot-greeting{grid-template-columns:1fr;gap:8px;margin-top:22px}.sambot-prompt-card{min-height:68px;padding:12px}.empty{margin:8vh auto!important}.chat{padding:20px 12px 155px!important}.wrap{max-width:94%}.controls{align-items:center}.tools{flex-wrap:wrap}.toolbtn{padding:7px 8px;font-size:11px}.top-actions .iconbtn{padding:7px 8px}.status{display:none}}
    @media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
  `;
  document.head.appendChild(premiumStyle);
  const greeting=document.querySelector('.empty');
  if(greeting&&!greeting.querySelector('.sambot-greeting')){
    const cards=document.createElement('div');cards.className='sambot-greeting';
    const suggestions=[
      ['✦','Build something','Plan an impressive app idea and build it step by step.'],
      ['⌘','Code & debug','Help me debug code and explain the fix clearly.'],
      ['◈','Learn anything','Teach me a difficult topic using simple examples.'],
      ['▤','Analyze a file','I want to analyze a file or dataset I upload.']
    ];
    suggestions.forEach(([icon,title,desc])=>{const b=document.createElement('button');b.className='sambot-prompt-card';const strong=document.createElement('b');strong.textContent=icon+'  '+title;const span=document.createElement('span');span.textContent=desc;b.append(strong,span);b.onclick=()=>{const input=document.querySelector('#box');if(input){input.value=desc;input.focus();input.dispatchEvent(new Event('input',{bubbles:true}));}};cards.appendChild(b)});
    greeting.appendChild(cards);
  }
  // Ctrl/Cmd+K command palette, with keyboard-accessible navigation.
  const commandOverlay=document.createElement('div');commandOverlay.id='sambotCommandOverlay';
  commandOverlay.innerHTML='<div id="sambotCommandBox" role="dialog" aria-modal="true" aria-label="Sambot command palette"><input id="sambotCommandInput" placeholder="Search actions… (try calculator, theme, export)" autocomplete="off"><div id="sambotCommandResults"></div><div id="sambotCommandHint">↑ ↓ to navigate · Enter to run · Esc to close</div></div>';
  document.body.appendChild(commandOverlay);
  const commandInput=commandOverlay.querySelector('#sambotCommandInput'),commandResults=commandOverlay.querySelector('#sambotCommandResults');
  const commands=[
    ['New chat','Start a fresh conversation','Ctrl+Shift+O',()=>document.querySelector('.new')?.click()],
    ['Search chats','Find a conversation','',()=>{const s=document.querySelector('#search');s?.focus();}],
    ['Calculator','Calculate a math expression','',()=>document.querySelector('button[onclick="openCalculator()"]')?.click()],
    ['Capabilities','Show available Sambot features','',()=>document.querySelector('button[onclick="showCapabilities()"]')?.click()],
    ['Library','Open saved items','',()=>document.querySelector('#sambotExtraNav [data-action="library"]')?.click()],
    ['Scheduled reminders','Open browser reminders','',()=>document.querySelector('#sambotExtraNav [data-action="scheduled"]')?.click()],
    ['Explore workflows','Browse quick actions','',()=>document.querySelector('#sambotExtraNav [data-action="explore"]')?.click()],
    ['Coding workspace','Open coding shortcuts','',()=>document.querySelector('#sambotExtraNav [data-action="codex"]')?.click()],
    ['Toggle appearance','Switch light/dark theme','',()=>document.querySelector('button[onclick="toggleTheme()"]')?.click()],
    ['Export current chat as PDF','Print or save as PDF','',()=>window.print()],
    ['Export all chats','Download chat history','',()=>document.querySelector('button[onclick="exportChats()"]')?.click()],
    ['Voice mode','Start hands-free voice chat','',()=>document.querySelector('#voiceModeBtn')?.click()]
  ];
  let commandIndex=0,filteredCommands=commands;
  function drawCommands(){
    const q=commandInput.value.trim().toLowerCase();
    filteredCommands=commands.filter(c=>(c[0]+' '+c[1]).toLowerCase().includes(q));commandResults.innerHTML='';commandIndex=Math.min(commandIndex,Math.max(0,filteredCommands.length-1));
    filteredCommands.forEach((c,i)=>{const d=document.createElement('div');d.className='sambot-command-item'+(i===commandIndex?' active':'');const label=document.createElement('span');label.textContent=c[0]+' — '+c[1];const key=document.createElement('span');key.className='sambot-shortcut';key.textContent=c[2]||'↵';d.append(label,key);d.onclick=()=>runCommand(i);commandResults.appendChild(d)});
    if(!filteredCommands.length)commandResults.innerHTML='<div class="sambot-command-item">No matching actions</div>';
  }
  function openCommands(){commandOverlay.classList.add('open');commandInput.value='';commandIndex=0;drawCommands();setTimeout(()=>commandInput.focus(),0)}
  function closeCommands(){commandOverlay.classList.remove('open')}
  function runCommand(i){const c=filteredCommands[i];if(!c)return;closeCommands();try{c[3]()}catch(e){console.error('Sambot command failed',e)}}
  commandInput.addEventListener('input',()=>{commandIndex=0;drawCommands()});
  commandInput.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();commandIndex=(commandIndex+1)%Math.max(1,filteredCommands.length);drawCommands()}else if(e.key==='ArrowUp'){e.preventDefault();commandIndex=(commandIndex-1+filteredCommands.length)%Math.max(1,filteredCommands.length);drawCommands()}else if(e.key==='Enter'){e.preventDefault();runCommand(commandIndex)}else if(e.key==='Escape')closeCommands()});
  commandOverlay.addEventListener('click',e=>{if(e.target===commandOverlay)closeCommands()});
  document.addEventListener('keydown',e=>{
    const mac=/Mac|iPhone|iPad/.test(navigator.platform),mod=mac?e.metaKey:e.ctrlKey;
    if(mod&&e.key.toLowerCase()==='k'){e.preventDefault();openCommands()}
    if(mod&&e.shiftKey&&e.key.toLowerCase()==='o'){e.preventDefault();document.querySelector('.new')?.click()}
    if(e.key==='Escape'&&commandOverlay.classList.contains('open'))closeCommands();
  });
  const paletteHint=document.createElement('button');paletteHint.className='iconbtn';paletteHint.textContent='⌕ Actions';paletteHint.title='Command palette (Ctrl+K)';paletteHint.onclick=openCommands;
  const topActionContainer=document.querySelector('.top-actions');if(topActionContainer)topActionContainer.prepend(paletteHint);

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
