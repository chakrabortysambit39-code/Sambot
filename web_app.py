import os
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import UploadFile, File
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="SAMBOT X")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    web_search: bool = False
    model: str | None = None
    memory: str | None = None
    instructions: str | None = None

class ImageRequest(BaseModel):
    prompt: str

HTML = r"""<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAMBOT X</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#08090c;color:#f5f5f5;height:100vh;overflow:hidden}
button,input,textarea{font:inherit}.app{height:100vh;display:flex}.sidebar{width:280px;background:#0e1014;border-right:1px solid #252831;display:flex;flex-direction:column;padding:12px;flex-shrink:0}.brand{font-weight:800;font-size:19px;padding:8px}.brand small{opacity:.4;font-size:9px;margin-left:5px}.new{width:100%;border:1px solid #30343d;background:#171a20;color:#fff;border-radius:10px;padding:11px;text-align:left;cursor:pointer;font-weight:700}.new:hover,.chatitem:hover,.sidebtn:hover{background:#20242c}.search{margin:10px 0}.search input{width:100%;background:#171a20;border:1px solid #2c3038;color:#fff;border-radius:9px;padding:9px 10px;outline:0}.history-title{font-size:10px;color:#777b86;padding:7px}.history{flex:1;overflow:auto}.chatitem{display:flex;align-items:center;gap:6px;padding:9px 7px;border-radius:9px;cursor:pointer;margin:2px 0}.chatitem.active{background:#242832}.chatname{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;font-size:13px}.menu{border:0;background:transparent;color:#999;cursor:pointer}.sidebottom{border-top:1px solid #252831;padding-top:8px}.sidebtn{width:100%;background:transparent;border:0;color:#ddd;text-align:left;padding:10px 8px;border-radius:9px;cursor:pointer}.profile{display:flex;align-items:center;gap:9px;padding:10px 6px}.avatar{width:30px;height:30px;border-radius:50%;background:#303641;display:grid;place-items:center}.main{flex:1;min-width:0;display:flex;flex-direction:column}.topbar{height:62px;border-bottom:1px solid #252831;display:flex;align-items:center;justify-content:space-between;padding:0 18px}.model{font-weight:700}.status{font-size:10px;opacity:.4;margin-left:7px}.top-actions{display:flex;gap:7px}.iconbtn,.toolbtn{border:1px solid #2c3038;background:#15181e;color:#ddd;border-radius:9px;padding:8px 10px;cursor:pointer}.chat{flex:1;overflow:auto;padding:28px 20px 150px}.empty{max-width:720px;margin:12vh auto;text-align:center}.empty h1{font-size:38px;margin:0 0 9px}.empty p{opacity:.45}.row{display:flex;margin:16px 0}.row.user{justify-content:flex-end}.wrap{max-width:min(820px,88%)}.msg{padding:14px 16px;border-radius:18px;line-height:1.55;white-space:normal;overflow-wrap:anywhere;background:#15181e}.msg p{margin:0 0 10px}.msg p:last-child{margin-bottom:0}.msg pre{position:relative;white-space:pre;overflow:auto;background:#080a0e;border:1px solid #30343d;border-radius:10px;padding:14px;margin:10px 0}.msg code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.92em}.msg :not(pre)>code{background:#2a2e37;border-radius:5px;padding:2px 5px}.msg blockquote{border-left:3px solid #5e687a;padding-left:12px;margin:8px 0;opacity:.85}.msg ul,.msg ol{padding-left:24px}.msg a{color:#7dd3fc;text-decoration:underline}.code-copy{float:right;border:1px solid #424855;background:#20242c;color:#ddd;border-radius:6px;padding:4px 7px;cursor:pointer;font-size:11px}.message-edit{margin-left:5px}.user .msg{background:#2c3039}.actions{display:flex;gap:5px;margin-top:6px}.mini{font-size:11px;border:1px solid #292d35;background:transparent;color:#999;border-radius:7px;padding:4px 7px;cursor:pointer}.image-result{display:block;max-width:100%;border-radius:14px}.thinking{opacity:.55}.composer{position:fixed;bottom:0;left:280px;right:0;display:flex;justify-content:center;padding:12px 18px 18px;background:linear-gradient(transparent,#08090c 25%)}.compose{width:min(900px,100%);background:#15181e;border:1px solid #343842;border-radius:18px;padding:10px;box-shadow:0 10px 35px #0009}.compose textarea{width:100%;min-height:48px;max-height:180px;resize:none;background:transparent;border:0;outline:0;color:#fff;padding:8px}.controls{display:flex;justify-content:space-between;gap:8px}.tools{display:flex;gap:6px}.toolbtn{padding:7px 10px;font-size:12px}.voice-active{background:#7f1d1d!important;color:#fff!important;border-color:#ef4444!important}.send{background:#fff;color:#000;font-weight:700}.modal{position:fixed;inset:0;background:#0009;display:none;align-items:center;justify-content:center;z-index:50}.modal.show{display:flex}.panel{width:min(500px,92%);background:#171a20;border:1px solid #343842;border-radius:16px;padding:20px}.panel h2{margin-top:0}.panel label{display:block;font-size:12px;opacity:.65;margin:14px 0 6px}.panel input{width:100%;background:#0e1014;border:1px solid #30343d;color:#fff;border-radius:8px;padding:10px}.panel button{margin-top:12px}.chat-action-panel{width:min(360px,92%);background:#171a20;border:1px solid #343842;border-radius:16px;padding:18px;box-shadow:0 20px 60px #0009}.chat-action-panel h3{margin:0 0 8px;font-size:17px}.chat-action-panel p{margin:0 0 14px;color:#a7abb5;font-size:13px;line-height:1.45}.chat-action-btn{display:flex;align-items:center;gap:10px;width:100%;margin:6px 0!important;padding:11px 12px;border:1px solid #30343d;border-radius:10px;background:#20242c;color:#f5f5f5;text-align:left;cursor:pointer}.chat-action-btn:hover{background:#2b303a}.chat-action-btn.danger{color:#ff7777;border-color:#593239}.chat-action-btn.danger:hover{background:#351d22}.chat-action-btn.cancel{justify-content:center;background:transparent;color:#b7bac3}.chat-action-panel input{width:100%;background:#0e1014;border:1px solid #454b58;color:#fff;border-radius:9px;padding:11px;margin:8px 0 12px}.light .chat-action-panel{background:#fff;color:#111;border-color:#ddd}.light .chat-action-panel p{color:#555}.light .chat-action-btn{background:#f5f5f6;color:#111;border-color:#ddd}.light .chat-action-btn.danger{color:#b42332;border-color:#efb9bf}.light .chat-action-panel input{background:#fff;color:#111;border-color:#ccc}.mobile{display:none}
.light{background:#f7f7f8;color:#111}.light .sidebar,.light .topbar,.light .compose,.light .msg,.light .new,.light .search input,.light .iconbtn,.light .toolbtn,.light .panel{background:#fff;color:#111}.light .sidebar,.light .topbar{border-color:#ddd}.light textarea{color:#111}.light .user .msg{background:#e4e5e8}.light .chatitem:hover{background:#eee}
@media(max-width:760px){.sidebar{position:fixed;z-index:40;left:-292px;top:0;bottom:0;transition:.2s}.sidebar.open{left:0}.composer{left:0}.mobile{display:inline-block}.topbar{height:58px}.empty h1{font-size:28px}}

/* Clean, readable layout fixes */
.sidebar{width:268px;min-width:268px;max-width:268px;padding:12px 10px 8px;overflow:hidden}
.brand{flex:0 0 auto;padding:10px 8px 14px}
.new{flex:0 0 auto}
.search{flex:0 0 auto;margin:9px 0 5px}
.history-title{flex:0 0 auto;margin-top:3px}
.history{display:flex;flex-direction:column;flex:1 1 auto;min-height:100px;overflow-y:auto;overscroll-behavior:contain;padding:2px 0 10px}
.chatitem{flex:0 0 auto;min-height:38px}
.sidebottom{flex:0 0 auto;max-height:44vh;overflow-y:auto;overscroll-behavior:contain;padding-top:5px;background:inherit}
.sidebtn{padding:8px 8px;font-size:13px;line-height:1.25}
.profile{padding:8px 6px}
.main{height:100vh;min-height:0;overflow:hidden}
.chat{min-height:0;overscroll-behavior:contain;padding:24px clamp(14px,3vw,36px) 180px}
.row{width:100%}
.wrap{max-width:min(820px,94%);min-width:0}
.msg{overflow-wrap:anywhere;word-break:normal}
.msg h1,.msg h2,.msg h3{line-height:1.3;margin:12px 0 8px}
.msg p{line-height:1.65}
.composer{left:268px;padding:10px 16px 14px}
.compose{width:min(850px,100%)}
.controls{align-items:center;flex-wrap:wrap}
.tools{align-items:center;flex-wrap:wrap}
.history-empty{padding:10px 8px;color:#777e8a;font-size:12px;line-height:1.5}
@media(max-width:760px){
 .sidebar{width:280px;min-width:280px;max-width:280px;max-height:100dvh}
 .sidebottom{max-height:38vh}
 .composer{left:0;padding:8px 10px 12px}
 .chat{padding:18px 10px 190px}
 .wrap{max-width:96%}
 .controls{align-items:flex-start}
}

/* Butter-smooth motion and interaction polish */
html{scroll-behavior:smooth}
body,.sidebar,.main,.topbar,.compose,.msg,.chatitem,.sidebtn,.toolbtn,.iconbtn,.new,.mini,.send,.panel,.chat-action-panel{
 transition:background-color .18s ease,border-color .18s ease,color .18s ease,box-shadow .2s ease,transform .18s cubic-bezier(.2,.75,.25,1),opacity .18s ease;
}
button{touch-action:manipulation;-webkit-tap-highlight-color:transparent}
button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid #8aa9e8;outline-offset:2px}
.chat{scrollbar-gutter:stable;scroll-padding-bottom:180px}
.chat::-webkit-scrollbar,.history::-webkit-scrollbar,.sidebottom::-webkit-scrollbar{width:8px}
.chat::-webkit-scrollbar-thumb,.history::-webkit-scrollbar-thumb,.sidebottom::-webkit-scrollbar-thumb{background:#343a46;border:2px solid transparent;background-clip:padding-box;border-radius:20px}
.chat::-webkit-scrollbar-thumb:hover,.history::-webkit-scrollbar-thumb:hover,.sidebottom::-webkit-scrollbar-thumb:hover{background:#50596a;border:2px solid transparent;background-clip:padding-box}
.chatitem{min-height:39px;position:relative}
.chatitem:hover{transform:translateX(2px)}
.chatitem.active{box-shadow:inset 2px 0 #8aa9e8}
.chatname{min-width:0}
.menu{flex:0 0 auto;opacity:.6}
.chatitem:hover .menu,.chatitem.active .menu{opacity:1}
.new:hover,.toolbtn:hover,.iconbtn:hover,.sidebtn:hover,.mini:hover{transform:translateY(-1px)}
.new:active,.toolbtn:active,.iconbtn:active,.sidebtn:active,.mini:active,.send:active{transform:scale(.98)}
.compose{transition:border-color .2s ease,box-shadow .22s ease,background-color .2s ease}
.compose textarea{transition:height .12s ease}
.row{animation:sambotRowIn .18s ease-out both}
@keyframes sambotRowIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.msg{contain:layout style;line-height:1.68}
.msg pre{max-width:100%;overscroll-behavior-x:contain;scrollbar-width:thin}
.msg img,.image-result{height:auto;max-height:70vh;object-fit:contain}
.composer{padding-bottom:max(14px,env(safe-area-inset-bottom))}
.compose{backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
.send{transition:transform .12s ease,opacity .12s ease,background-color .15s ease}
.send:hover{box-shadow:0 3px 14px #0003}
#sambotUiModal,#sambotCommandOverlay{backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px)}
.sambot-ui-card,#sambotCommandBox{animation:sambotModalIn .16s cubic-bezier(.2,.75,.25,1) both}
@keyframes sambotModalIn{from{opacity:0;transform:translateY(7px) scale(.99)}to{opacity:1;transform:translateY(0) scale(1)}}
@media(max-width:760px){
 .sidebar{box-shadow:12px 0 40px #0005}
 .sidebar.open{animation:sambotSidebarIn .18s ease-out}
 @keyframes sambotSidebarIn{from{transform:translateX(-8px);opacity:.85}to{transform:translateX(0);opacity:1}}
 .chatitem:hover{transform:none}
}
@media(prefers-reduced-motion:reduce){
 html{scroll-behavior:auto}
 *,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}
}
/* Sidebar cleanup */
.sidebar{width:268px;min-width:268px;max-width:268px;padding:12px 10px 8px;gap:0}
.history{flex:1 1 auto;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:3px 0 10px}
.sidebottom{flex:0 0 auto;max-height:none;overflow:visible;border-top:1px solid #252831;padding-top:7px;background:transparent}
.side-tools{border-radius:10px;overflow:hidden}
.side-tools summary{list-style:none;cursor:pointer;padding:10px 9px;border-radius:9px;font-size:13px;color:#c9ced8;user-select:none}
.side-tools summary::-webkit-details-marker{display:none}
.side-tools summary:after{content:'⌄';float:right;color:#828b9b}
.side-tools[open] summary:after{content:'⌃'}
.side-tools summary:hover{background:#1b1f27}
.side-tools-list{max-height:34vh;overflow:auto;padding:3px 0 5px;overscroll-behavior:contain}
.side-tools-list .sidebtn{padding:8px 10px;font-size:12px;color:#b8bfcb}
.profile{border-top:1px solid #252831;margin-top:5px;padding:9px 6px 5px;flex:0 0 auto}
.chat{padding:24px clamp(14px,3vw,36px) 178px}
.row{margin:18px 0}
.wrap{max-width:min(800px,94%)}
.msg{padding:15px 17px;border-radius:16px;line-height:1.7}
.assistant .msg{background:#14161b}
.user .msg{background:#242832}
.chat::-webkit-scrollbar,.history::-webkit-scrollbar,.side-tools-list::-webkit-scrollbar{width:6px}
.chat::-webkit-scrollbar-thumb,.history::-webkit-scrollbar-thumb,.side-tools-list::-webkit-scrollbar-thumb{background:#3b414d;border-radius:8px}
.composer{left:268px;padding:10px 16px 14px;background:linear-gradient(transparent,#08090c 30%)}
.compose{border-radius:20px;width:min(850px,100%)}
@media(max-width:760px){.sidebar{width:280px;min-width:280px;max-width:280px}.composer{left:0}.side-tools-list{max-height:30vh}}
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
<details class="side-tools"><summary>⚙ Tools & settings</summary><div class="side-tools-list">
<button class="sidebtn" onclick="openSettings()">Settings</button><button class="sidebtn" onclick="exportChats()">Export chats</button><button class="sidebtn" onclick="openCalculator()">Calculator</button><button class="sidebtn" onclick="showCapabilities()">Capabilities</button><button class="sidebtn" onclick="exportCurrentChatMarkdown()">Export current chat (.md)</button><button class="sidebtn" onclick="document.getElementById('importChatsInput').click()">Import chats</button><input id="importChatsInput" type="file" accept=".json,application/json" hidden><button class="sidebtn" onclick="clearAllChats()">Clear all chats</button><button class="sidebtn" onclick="toggleMemory()">Memory</button><button class="sidebtn" onclick="toggleTheme()">Appearance</button>
</div></details><div class="profile"><div class="avatar">S</div><div><b>Sambot X</b><div style="font-size:10px;opacity:.55">AI workspace · local chats</div></div></div></div>
</aside>
<section class="main">
<header class="topbar">
<div><button class="iconbtn mobile" onclick="toggleSidebar()">☰</button><span class="model">SAMBOT X</span><span class="status">Groq + Cloudflare AI</span></div>
<div class="top-actions"><button class="iconbtn" onclick="newChat()">＋ New</button></div>
</header>
<section class="chat" id="chat"></section>
<div class="composer"><div class="compose">
<textarea id="box" rows="2" placeholder="Message Sambot X..."></textarea>
<div class="controls"><div class="tools"><input id="fileInput" type="file" hidden multiple accept=".txt,.md,.csv,.json,.pdf,.docx,.xlsx,.py,.js,.html,.css"><button class="toolbtn" onclick="document.getElementById('fileInput').click()">📎 Files</button><button class="toolbtn" id="webBtn" onclick="toggleWeb()">🌐 Web</button><button class="toolbtn" id="dataAnalysisBtn" onclick="toggleDataAnalysis()" title="Analyze attached CSV, spreadsheet, or table">📊 Analyze data</button><button class="toolbtn" id="mic" onclick="voice()">🎙 Voice input</button><button class="toolbtn" id="voiceModeBtn" onclick="startVoiceMode()">🎧 Voice mode</button></div><div class="tools"><button class="toolbtn" id="stopBtn" onclick="stopGeneration()" style="display:none">■ Stop</button><button class="toolbtn send" id="sendBtn" onclick="send()">Send ➤</button></div></div>
<div id="attachments" style="font-size:11px;opacity:.6;padding:4px"></div><div id="voiceStatus" aria-live="polite" style="font-size:11px;opacity:.65;padding:2px 4px"></div><div style="text-align:center;font-size:10px;opacity:.35;padding:5px">Enter to send • Shift+Enter for new line • Type “create image …” for images • Web searches current information</div>
</div></div>
</section>
</div>

<div class="modal" id="chatActionModal" onclick="if(event.target===this)closeChatAction()"><div class="chat-action-panel" id="chatActionPanel"></div></div>
<div class="modal" id="settings"><div class="panel">
<h2>⚙ Settings</h2>
<label>Display name</label><input id="displayName" placeholder="Sambot User">
<label>Custom instructions for Sambot</label><textarea id="customInstructions" rows="4" placeholder="How should Sambot respond?"></textarea><label>Voice language</label><select id="voiceLanguage" style="width:100%;background:#0e1014;border:1px solid #30343d;color:#fff;border-radius:8px;padding:10px"><option value="en-IN">English (India)</option><option value="en-US">English (US)</option><option value="hi-IN">Hindi</option><option value="bn-IN">Bengali</option><option value="mr-IN">Marathi</option><option value="es-ES">Spanish</option><option value="fr-FR">French</option><option value="de-DE">German</option><option value="ja-JP">Japanese</option></select><label>Speech speed</label><input id="voiceRate" type="range" min="0.7" max="1.3" step="0.1" value="1" style="width:100%"><label>About</label><div style="opacity:.55;font-size:12px">SAMBOT X • Groq chat • Cloudflare image generation</div>
<button class="toolbtn" onclick="saveSettings()">Save</button>
<button class="toolbtn" onclick="closeSettings()">Close</button>
</div></div>

<script>let webEnabled=false,dataAnalysisEnabled=false,attachedFiles=[];
const box=document.getElementById('box'),chat=document.getElementById('chat'),historyEl=document.getElementById('history'),sidebar=document.getElementById('sidebar');
let sessions=[];try{const stored=JSON.parse(localStorage.getItem('sambot_sessions')||'[]');sessions=Array.isArray(stored)?stored.filter(s=>s&&typeof s==='object'&&Array.isArray(s.messages)).map(s=>({id:String(s.id||('chat-'+Date.now()+'-'+Math.random())),title:typeof s.title==='string'?s.title:'New chat',messages:s.messages.filter(m=>m&&typeof m==='object'&&['user','assistant'].includes(m.role)).map(m=>({role:m.role,content:typeof m.content==='string'?m.content:'',...(typeof m.image==='string'?{image:m.image}:{})}))})):[]}catch(e){console.warn('SAMBOT_HISTORY_RECOVERY',e);sessions=[];try{localStorage.removeItem('sambot_sessions')}catch(_){}}let currentId=localStorage.getItem('sambot_current')||'';
let theme=localStorage.getItem('sambot_theme')||'dark';
if(theme==='light')document.body.classList.add('light');
function save(){try{localStorage.setItem('sambot_sessions',JSON.stringify(sessions));localStorage.setItem('sambot_current',currentId)}catch(e){console.warn('Storage unavailable',e)}}
function current(){return sessions.find(x=>x.id===currentId)}
function titleFor(s){return s.title||((s.messages.find(m=>m.role==='user')||{}).content||'New chat').slice(0,36)}
function ensure(){if(!currentId||!current()){currentId=Date.now().toString();sessions.unshift({id:currentId,title:'New chat',messages:[]});save()}}
function renderHistory(){ensure();const q=(document.getElementById('search').value||'').trim().toLowerCase();historyEl.innerHTML='';const visible=sessions.filter(s=>titleFor(s).toLowerCase().includes(q));if(!visible.length){const empty=document.createElement('div');empty.className='history-empty';empty.textContent=q?'No chats match your search.':'Your conversations will appear here.';historyEl.appendChild(empty);return}visible.forEach(s=>{const d=document.createElement('div');d.className='chatitem '+(s.id===currentId?'active':'');const n=document.createElement('span');n.className='chatname';n.textContent=titleFor(s);n.title=titleFor(s);n.onclick=()=>loadChat(s.id);const m=document.createElement('button');m.className='menu';m.textContent='⋯';m.setAttribute('aria-label','Options for '+titleFor(s));m.onclick=e=>{e.stopPropagation();chatMenu(s.id)};d.append(n,m);historyEl.appendChild(d)})}
function renderChat(){try{chat.innerHTML='';const s=current();if(!s||!Array.isArray(s.messages)||!s.messages.length){chat.innerHTML='<div class="empty"><h1>How can I help?</h1><p>Chat, code, write, study, brainstorm — or type <b>create image</b>.</p></div>';return}s.messages.forEach(m=>{if(m&&typeof m==='object'&&['user','assistant'].includes(m.role))drawMessage(m)})}catch(e){console.error('SAMBOT_RENDER_ERROR',e);chat.innerHTML='<div class="row assistant"><div class="wrap"><div class="msg">The chat display hit an error. Your message may still be saved. Click New chat and try again, or refresh the page.</div></div></div>'}}
function escapeHTML(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function inlineMarkdown(s){let x=escapeHTML(s);x=x.replace(/\x60([^\x60]+)\x60/g,'<code>$1</code>');x=x.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');x=x.replace(/__([^_]+)__/g,'<strong>$1</strong>');x=x.replace(/\*([^*\n]+)\*/g,'<em>$1</em>');x=x.replace(/_([^_\n]+)_/g,'<em>$1</em>');x=x.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');return x}
function renderMarkdown(source){const lines=String(source||'').replace(/<br\s*\/?\s*>/gi,'\n').replace(/\r/g,'').split('\n');let out='',paragraph=[],list='',code=false,codeLang='',codeLines=[];const flushP=()=>{if(paragraph.length){out+='<p>'+paragraph.map(inlineMarkdown).join('<br>')+'</p>';paragraph=[]}};const flushList=()=>{if(list){out+='</'+list+'>';list=''}};for(const line of lines){const fence=line.match(/^\s*```\s*([\w+-]*)/);if(fence){flushP();flushList();if(!code){code=true;codeLang=fence[1]||'';codeLines=[]}else{const raw=escapeHTML(codeLines.join('\n'));out+='<pre><button class="code-copy" type="button" onclick="copyCode(this)">Copy code</button><code'+(codeLang?' class="language-'+escapeHTML(codeLang)+'"':'')+'>'+raw+'</code></pre>';code=false;codeLang='';codeLines=[]}continue}if(code){codeLines.push(line);continue}if(!line.trim()){flushP();flushList();continue}if(/^\s*([-*_])\1\1+\s*$/.test(line)){flushP();flushList();out+='<hr>';continue}const h=line.match(/^\s{0,3}(#{1,6})\s+(.+)$/);if(h){flushP();flushList();const n=h[1].length;out+='<h'+n+'>'+inlineMarkdown(h[2])+'</h'+n+'>';continue}const q=line.match(/^\s*>\s?(.*)$/);if(q){flushP();flushList();out+='<blockquote>'+inlineMarkdown(q[1])+'</blockquote>';continue}const ul=line.match(/^\s*[-*+]\s+(.+)$/),ol=line.match(/^\s*\d+[.)]\s+(.+)$/);if(ul||ol){flushP();const type=ul?'ul':'ol';if(list!==type){flushList();list=type;out+='<'+type+'>'}out+='<li>'+inlineMarkdown((ul||ol)[1])+'</li>';continue}flushList();paragraph.push(line)}if(code){out+='<pre><code>'+escapeHTML(codeLines.join('\n'))+'</code></pre>'}flushP();flushList();return out}
function copyCode(btn){const code=btn.parentElement.querySelector('code');navigator.clipboard?.writeText(code?.textContent||'').then(()=>{btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy code',1200)}).catch(()=>{})}
function editUserMessage(index){const s=current();if(!s||!s.messages[index]||s.messages[index].role!=='user')return;box.value=s.messages[index].content||'';s.messages=s.messages.slice(0,index);save();renderChat();box.focus();box.setSelectionRange(box.value.length,box.value.length)}
function drawMessage(m){const row=document.createElement('div');row.className='row '+m.role;const wrap=document.createElement('div');wrap.className='wrap';const msg=document.createElement('div');msg.className='msg';if(m.image){const img=document.createElement('img');img.className='image-result';img.src=m.image;msg.appendChild(img)}else msg.innerHTML=renderMarkdown(m.content||'');wrap.appendChild(msg);if((m.role==='assistant'||m.role==='user')&&!m.image){const acts=document.createElement('div');acts.className='actions';if(m.role==='assistant'){const cp=document.createElement('button');cp.className='mini';cp.textContent='Copy';cp.onclick=()=>navigator.clipboard?.writeText(m.content||'');acts.appendChild(cp);const sp=document.createElement('button');sp.className='mini';sp.textContent='🔊';sp.onclick=()=>speakText(m.content||'');acts.appendChild(sp);const rg=document.createElement('button');rg.className='mini';rg.textContent='↻ Regenerate';rg.onclick=()=>regenerate();acts.appendChild(rg)}else{const edit=document.createElement('button');edit.className='mini message-edit';edit.textContent='✎ Edit';const s=current();const index=s?s.messages.indexOf(m):-1;edit.onclick=()=>editUserMessage(index);acts.appendChild(edit)}wrap.appendChild(acts)}row.appendChild(wrap);chat.appendChild(row)}
function loadChat(id){currentId=id;save();renderHistory();renderChat();sidebar.classList.remove('open')}
function newChat(){currentId=Date.now().toString();sessions.unshift({id:currentId,title:'New chat',messages:[]});save();renderHistory();renderChat();box.focus()}
let activeChatActionId=null;
function closeChatAction(){document.getElementById('chatActionModal').classList.remove('show');activeChatActionId=null}
function chatMenu(id){const s=sessions.find(x=>x.id===id);if(!s)return;activeChatActionId=id;const panel=document.getElementById('chatActionPanel');panel.innerHTML='';const heading=document.createElement('h3');heading.textContent='Chat options';const description=document.createElement('p');description.textContent=titleFor(s);const rename=document.createElement('button');rename.className='chat-action-btn';rename.textContent='✏️ Rename chat';rename.onclick=()=>showRenameChat(id);const del=document.createElement('button');del.className='chat-action-btn danger';del.textContent='🗑️ Delete chat';del.onclick=()=>showDeleteChat(id);const cancel=document.createElement('button');cancel.className='chat-action-btn cancel';cancel.textContent='Cancel';cancel.onclick=closeChatAction;panel.append(heading,description,rename,del,cancel);document.getElementById('chatActionModal').classList.add('show')}
function showRenameChat(id){const s=sessions.find(x=>x.id===id);if(!s)return;const panel=document.getElementById('chatActionPanel');panel.innerHTML='';const heading=document.createElement('h3');heading.textContent='Rename chat';const input=document.createElement('input');input.id='renameChatInput';input.maxLength=80;input.value=titleFor(s);input.setAttribute('aria-label','Chat name');const saveBtn=document.createElement('button');saveBtn.className='chat-action-btn';saveBtn.textContent='Save name';saveBtn.onclick=()=>{const name=input.value.trim();if(!name){input.focus();return}s.title=name;save();renderHistory();closeChatAction()};const cancel=document.createElement('button');cancel.className='chat-action-btn cancel';cancel.textContent='Cancel';cancel.onclick=()=>chatMenu(id);panel.append(heading,input,saveBtn,cancel);input.focus();input.select();input.addEventListener('keydown',e=>{if(e.key==='Enter')saveBtn.click();if(e.key==='Escape')closeChatAction()})}
function showDeleteChat(id){const s=sessions.find(x=>x.id===id);if(!s)return;const panel=document.getElementById('chatActionPanel');panel.innerHTML='';const heading=document.createElement('h3');heading.textContent='Delete this chat?';const description=document.createElement('p');description.textContent='“'+titleFor(s)+'” will be removed from this browser. This cannot be undone.';const del=document.createElement('button');del.className='chat-action-btn danger';del.textContent='Delete chat';del.onclick=()=>{sessions=sessions.filter(x=>x.id!==id);if(currentId===id)currentId='';ensure();save();renderHistory();renderChat();closeChatAction()};const back=document.createElement('button');back.className='chat-action-btn cancel';back.textContent='Cancel';back.onclick=()=>chatMenu(id);panel.append(heading,description,del,back)}
function add(role,content,image){ensure();const s=current();if(!s)return;const message={role,content,image};s.messages.push(message);if(role==='user'&&s.title==='New chat')s.title=(content||'New chat').slice(0,36);save();renderChat();chat.scrollTop=chat.scrollHeight;renderHistory()}
function imageRequest(s){return /\b(create|generate|make|draw|render)\s+(an?\s+)?image\b/i.test(s)||/^\/image\b/i.test(s)}
function imagePrompt(s){return s.replace(/^\/image\s*/i,'').replace(/^\s*(create|generate|make|draw|render)\s+(an?\s+)?image\s*(of|showing)?\s*/i,'').trim()||s}
let activeController=null;
function setGenerating(on){document.getElementById('stopBtn').style.display=on?'inline-block':'none';document.getElementById('sendBtn').style.display=on?'none':'inline-block'}
function stopGeneration(){if(activeController){activeController.abort();activeController=null}setGenerating(false)}
async function send(){
 if(activeController)return;
 const text=box.value.trim();if(!text&&!attachedFiles.length)return;box.value="";ensure();
 const session=current();if(!session){showChatNotice("Could not open a chat session. Click New chat and try again.");return}
 if(text&&imageRequest(text)){await generateImage(imagePrompt(text),text);return}
 const controller=new AbortController();activeController=controller;setGenerating(true);let assistantMessage=null;
 try{
  session.messages.push({role:"user",content:text||"📎 Attached file(s)"});if(session.title==="New chat"&&text)session.title=text.slice(0,36);save();renderHistory();renderChat();chat.scrollTop=chat.scrollHeight;
  const fileText=await uploadFiles();let finalText=fileText?(text||"Please analyze the attached file(s).")+"\n\n[Attached file contents]\n"+fileText:text;
  if(dataAnalysisEnabled){if(!fileText)throw new Error("Attach a CSV, spreadsheet, or text file first, then enable Analyze data.");finalText="DATA ANALYSIS REQUEST: Analyze the supplied dataset carefully. Identify columns and data types, row count, missing values, useful descriptive statistics for numeric columns, category counts for categorical columns, notable trends/outliers, and answer the user's specific question. Show calculations where possible, clearly state assumptions, and do not invent values. Use Markdown tables.\n\nUSER QUESTION: "+(text||"Summarize and analyze this dataset.")+"\n\nDATA:\n"+fileText}
  const msgs=current().messages.filter(m=>!m.image&&m.content!=="Thinking…").slice(-20).map(m=>({role:m.role,content:m.content}));if(fileText)msgs[msgs.length-1]={role:"user",content:finalText};
  const response=await fetch("/api/chat/stream",{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,body:JSON.stringify({messages:msgs,web_search:webEnabled,memory:localStorage.getItem("sambot_memory")||"",instructions:localStorage.getItem("sambot_instructions")||""})});
  if(!response.ok){let j={};try{j=await response.json()}catch(_){}throw new Error(j.detail||j.error||("Server error HTTP "+response.status))}
  assistantMessage={role:"assistant",content:""};session.messages.push(assistantMessage);save();renderChat();const row=chat.lastElementChild,msgEl=row?.querySelector(".msg"),reader=response.body.getReader(),decoder=new TextDecoder();let buffer="",failed="";
  while(true){const part=await reader.read();if(part.done)break;buffer+=decoder.decode(part.value,{stream:true});const events=buffer.split("\n\n");buffer=events.pop()||"";for(const event of events){const line=event.split("\n").find(x=>x.startsWith("data: "));if(!line)continue;let data;try{data=JSON.parse(line.slice(6))}catch(_){continue}if(data.token){assistantMessage.content+=data.token;if(msgEl)msgEl.innerHTML=renderMarkdown(assistantMessage.content);chat.scrollTop=chat.scrollHeight}if(data.error)failed=data.error}if(failed)throw new Error(failed);save()}
  if(!assistantMessage.content)assistantMessage.content="The AI returned an empty response. Please try again.";save();renderChat();chat.scrollTop=chat.scrollHeight;if(voiceMode)speakText(assistantMessage.content);
 }catch(e){if(e.name==="AbortError"){if(assistantMessage&&assistantMessage.content){assistantMessage.content+="\n\n[Generation stopped]";save();renderChat()}}else{if(assistantMessage&&!assistantMessage.content){const s=current();if(s)s.messages=s.messages.filter(m=>m!==assistantMessage)}showChatNotice("Could not get a reply: "+(e?.message||String(e)))}}
 finally{if(activeController===controller)activeController=null;setGenerating(false);if(voiceMode&&!speechSynthesis.speaking){if(voiceRecognition){try{voiceRecognition.stop()}catch(e){}}voiceRestartTimer=setTimeout(listenForVoiceTurn,500)}}
}
function showChatNotice(message){
  try{add("assistant",message)}catch(_){
    const row=document.createElement("div");row.className="row assistant";
    const wrap=document.createElement("div");wrap.className="wrap";
    const msg=document.createElement("div");msg.className="msg";msg.textContent=message;
    wrap.appendChild(msg);row.appendChild(wrap);chat.appendChild(row);chat.scrollTop=chat.scrollHeight;
  }
}
async function generateImage(prompt,shown){add('user',shown);add('assistant','Creating your image…');const row=chat.lastElementChild;row.querySelector('.msg').classList.add('thinking');try{const r=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});const j=await r.json();chat.removeChild(row);if(j.image)add('assistant','',j.image);else add('assistant',j.error||'Image generation failed.')}catch(e){chat.removeChild(row);add('assistant','Image error: '+e.message)}}
async function regenerate(){const s=current();const last=s.messages.filter(m=>m.role==='user'&&!m.image).pop();if(!last)return;s.messages=s.messages.slice(0,-1);save();renderChat();box.value=last.content;await send()}
let voiceMode=false,voiceRecognition=null,voiceRestartTimer=null;
function voiceSupported(){return !!(window.SpeechRecognition||window.webkitSpeechRecognition)}
function voice(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R){showChatNotice('Voice input needs a browser with speech recognition, such as desktop Chrome.');return}const rec=new R();rec.lang='en-IN';rec.interimResults=false;rec.maxAlternatives=1;const b=document.getElementById('mic');b.textContent='⏺ Listening…';rec.onresult=e=>{box.value=e.results[0][0].transcript;box.focus()};rec.onend=()=>b.textContent='🎙 Voice input';rec.onerror=()=>b.textContent='🎙 Voice input';try{rec.start()}catch(e){b.textContent='🎙 Voice input';showChatNotice('Could not start microphone. Check browser microphone permission.')} }
function setVoiceStatus(text){const s=document.getElementById('voiceStatus');if(s)s.textContent=text}
function stopVoiceMode(){voiceMode=false;if(voiceRestartTimer){clearTimeout(voiceRestartTimer);voiceRestartTimer=null}if(voiceRecognition){try{voiceRecognition.onend=null;voiceRecognition.stop()}catch(e){}voiceRecognition=null}if('speechSynthesis'in window)speechSynthesis.cancel();const b=document.getElementById('voiceModeBtn');if(b){b.textContent='🎧 Voice mode';b.classList.remove('voice-active')}setVoiceStatus('Voice mode off')}
function startVoiceMode(){if(!voiceSupported()||!('speechSynthesis'in window)){showChatNotice('Voice mode needs speech recognition and speech synthesis. Try the latest desktop Chrome and allow microphone access.');return}if(voiceMode){stopVoiceMode();return}voiceMode=true;const b=document.getElementById('voiceModeBtn');b.textContent='■ Stop voice';b.classList.add('voice-active');setVoiceStatus('Listening… say your message');listenForVoiceTurn()}
function listenForVoiceTurn(){if(!voiceMode||activeController||(window.speechSynthesis&&speechSynthesis.speaking))return;const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R)return;try{const rec=new R();voiceRecognition=rec;rec.lang=localStorage.getItem('sambot_voice_lang')||'en-IN';rec.interimResults=false;rec.continuous=false;rec.maxAlternatives=1;rec.onstart=()=>setVoiceStatus('Listening…');rec.onresult=e=>{const heard=(e.results&&e.results[0]&&e.results[0][0]&&e.results[0][0].transcript||'').trim();if(heard&&voiceMode){box.value=heard;setVoiceStatus('Thinking…');send()}};rec.onerror=e=>{setVoiceStatus(e.error==='not-allowed'?'Microphone permission denied':'Voice input issue: '+e.error);if(e.error==='not-allowed')stopVoiceMode()};rec.onend=()=>{if(voiceRecognition===rec)voiceRecognition=null;if(voiceMode&&!activeController&&!(window.speechSynthesis&&speechSynthesis.speaking)){voiceRestartTimer=setTimeout(listenForVoiceTurn,700)}};rec.start()}catch(e){setVoiceStatus('Could not start microphone. Check permission.');voiceRestartTimer=setTimeout(listenForVoiceTurn,1200)}}
function speakText(t){if(!('speechSynthesis'in window)||!t)return;speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(String(t).replace(/[*_>#]/g,' '));utterance.lang=localStorage.getItem('sambot_voice_lang')||'en-IN';utterance.rate=Number(localStorage.getItem('sambot_voice_rate')||'1');utterance.onstart=()=>{if(voiceMode)setVoiceStatus('Speaking…')};utterance.onend=()=>{if(voiceMode){setVoiceStatus('Listening… say your next message');voiceRestartTimer=setTimeout(listenForVoiceTurn,400)}};utterance.onerror=()=>{if(voiceMode){setVoiceStatus('Listening…');voiceRestartTimer=setTimeout(listenForVoiceTurn,700)}};speechSynthesis.speak(utterance)}
function toggleTheme(){theme=theme==='dark'?'light':'dark';localStorage.setItem('sambot_theme',theme);document.body.classList.toggle('light',theme==='light')}
function toggleSidebar(){sidebar.classList.toggle('open')}
function openSettings(){document.getElementById('settings').classList.add('show');document.getElementById('displayName').value=localStorage.getItem('sambot_name')||'Sambot User';document.getElementById('customInstructions').value=localStorage.getItem('sambot_instructions')||'';document.getElementById('voiceLanguage').value=localStorage.getItem('sambot_voice_lang')||'en-IN';document.getElementById('voiceRate').value=localStorage.getItem('sambot_voice_rate')||'1'}
function closeSettings(){document.getElementById('settings').classList.remove('show')}
function saveSettings(){localStorage.setItem('sambot_name',document.getElementById('displayName').value||'Sambot User');localStorage.setItem('sambot_instructions',document.getElementById('customInstructions').value||'');localStorage.setItem('sambot_voice_lang',document.getElementById('voiceLanguage').value||'en-IN');localStorage.setItem('sambot_voice_rate',document.getElementById('voiceRate').value||'1');closeSettings();showChatNotice('Settings saved.')}
function downloadJSON(data,name){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function exportChats(){downloadJSON({format:'sambot-chats-v1',exportedAt:new Date().toISOString(),sessions,currentId},'sambot-chats.json')}
function exportCurrentChatMarkdown(){const s=current();if(!s){showChatNotice('Open a chat first.');return}const body='# '+(s.title||'Sambot chat')+'\n\n'+s.messages.map(m=>'## '+(m.role==='user'?'You':'Sambot X')+'\n\n'+(m.content||'')+(m.image?'\n\n[Image attached]':'')).join('\n\n---\n\n');const blob=new Blob([body],{type:'text/markdown;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=(s.title||'sambot-chat').replace(/[^a-z0-9-_]+/gi,'-').slice(0,60)+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function importChatsFile(file){const reader=new FileReader();reader.onload=()=>{try{const data=JSON.parse(reader.result);const incoming=Array.isArray(data)?data:data.sessions;if(!Array.isArray(incoming))throw new Error('This file does not contain Sambot chat history.');const valid=incoming.filter(s=>s&&Array.isArray(s.messages)).map(s=>({id:Date.now().toString()+Math.random().toString(16).slice(2),title:typeof s.title==='string'?s.title:'Imported chat',messages:s.messages.filter(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string').map(m=>({role:m.role,content:m.content,...(typeof m.image==='string'?{image:m.image}:{})}))}));if(!valid.length)throw new Error('No valid chats were found in this file.');sessions=[...valid,...sessions];currentId=valid[0].id;save();renderHistory();renderChat();alert('Imported '+valid.length+' chat(s).')}catch(e){alert('Could not import chats: '+e.message)}};reader.readAsText(file)}
function clearAllChats(){if(!sessions.length){alert('There are no chats to clear.');return}if(!confirm('Delete every saved chat from this browser? Export chats first if you want a backup.'))return;sessions=[];currentId='';ensure();save();renderHistory();renderChat()}
document.getElementById("fileInput").addEventListener("change",e=>{attachedFiles=Array.from(e.target.files||[]);document.getElementById("attachments").textContent=attachedFiles.length?"📎 "+attachedFiles.map(f=>f.name).join(", "):""});
document.getElementById('importChatsInput').addEventListener('change',e=>{const file=e.target.files&&e.target.files[0];if(file)importChatsFile(file);e.target.value=''});
box.addEventListener("paste",e=>{
  const items=Array.from(e.clipboardData?.items||[]);
  const imageItem=items.find(i=>i.type.startsWith("image/"));
  if(!imageItem)return;
  const file=imageItem.getAsFile();
  if(file){
    e.preventDefault();
    const ext=file.type.split("/")[1]||"png";
    const named=new File([file],"pasted-image."+ext,{type:file.type});
    attachedFiles.push(named);
    document.getElementById("attachments").textContent="📎 "+attachedFiles.map(f=>f.name).join(", ");
  }
});
function toggleWeb(){webEnabled=!webEnabled;document.getElementById("webBtn").style.background=webEnabled?"#2c3039":""}
function toggleDataAnalysis(){dataAnalysisEnabled=!dataAnalysisEnabled;const b=document.getElementById('dataAnalysisBtn');b.style.background=dataAnalysisEnabled?'#155e75':'';b.setAttribute('aria-pressed',String(dataAnalysisEnabled));showChatNotice(dataAnalysisEnabled?'Data analysis mode on: attach a CSV or spreadsheet and ask a question.':'Data analysis mode off.')}
async function openCalculator(){const expression=prompt('Basic calculator: enter an expression (example: (125*8)/5)');if(!expression)return;try{const r=await fetch('/api/tools/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:expression})});const j=await r.json();if(!r.ok)throw new Error(j.error||'Calculation failed');showChatNotice(expression+' = '+j.result)}catch(e){showChatNotice('Calculator: '+e.message)}}
async function showCapabilities(){try{const r=await fetch('/api/capabilities');const j=await r.json();const caps=j.capabilities||{};const lines=Object.entries(caps).map(([k,v])=>k+': '+v.join(', ')).join('\n');alert('Sambot X capabilities\n\n'+lines)}catch(e){showChatNotice('Could not load capabilities: '+e.message)}}
function toggleMemory(){const old=localStorage.getItem("sambot_memory")||"";const value=prompt("What should Sambot remember? (stored only in this browser)",old);if(value!==null)localStorage.setItem("sambot_memory",value)}
async function uploadFiles(){if(!attachedFiles.length)return "";const fd=new FormData();attachedFiles.forEach(f=>fd.append("files",f));const r=await fetch("/api/files",{method:"POST",body:fd});const j=await r.json();if(!r.ok)throw new Error(j.error||"File upload failed");attachedFiles=[];document.getElementById("fileInput").value="";document.getElementById("attachments").textContent="";return j.text||""}
box.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}})
window.newChat=newChat;window.send=send;window.toggleTheme=toggleTheme;window.openSettings=openSettings;window.closeSettings=closeSettings;window.saveSettings=saveSettings;window.exportChats=exportChats;window.toggleSidebar=toggleSidebar;window.voice=voice;window.regenerate=regenerate;window.chatMenu=chatMenu;window.loadChat=loadChat;ensure();renderHistory();renderChat();
</script>
</body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/health")
def health():
    return {"ok":True,"groq_configured":bool(os.getenv("GROQ_API_KEY")),"cloudflare_configured":bool(os.getenv("CLOUDFLARE_ACCOUNT_ID") and os.getenv("CLOUDFLARE_API_TOKEN")),"features":["chat","streaming_chat","stop_generation","model_selection","image_generation","image_understanding","web_search","file_uploads","markdown","voice_input","voice_mode","read_aloud","local_history","import_export","custom_instructions","local_memory"]}

def extract_file_text(file, raw):
    name=(file.filename or "").lower()
    if name.endswith((".txt",".md",".csv",".json",".py",".js",".html",".css")):
        return raw.decode("utf-8","ignore")[:120000]
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)[:120000]
        except Exception as e:
            return f"[PDF extraction unavailable: {e}]"
    if name.endswith(".docx"):
        try:
            from docx import Document
            import io
            return "\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)[:120000]
        except Exception as e:
            return f"[DOCX extraction unavailable: {e}]"
    if name.endswith((".xlsx",".xls")):
        try:
            from openpyxl import load_workbook
            import io
            wb=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
            out=[]
            for ws in wb.worksheets:
                out.append("SHEET: "+ws.title)
                for row in ws.iter_rows(values_only=True): out.append("\t".join("" if v is None else str(v) for v in row))
            return "\n".join(out)[:120000]
        except Exception as e:
            return f"[Spreadsheet extraction unavailable: {e}]"
    return f"[Uploaded file: {file.filename}. This file type is not text-extractable yet.]"

@app.post("/api/files")
async def files(files: list[UploadFile] = File(...)):
    if not files:return JSONResponse({"error":"No files uploaded."},status_code=400)
    parts=[]
    for f in files[:10]:
        raw=await f.read()
        if len(raw)>20*1024*1024:return JSONResponse({"error":f"{f.filename} is larger than 20 MB."},status_code=413)
        parts.append(f"FILE: {f.filename}\n{extract_file_text(f,raw)}")
    return {"ok":True,"text":"\n\n".join(parts)}

def web_search(query):
    try:
        from bs4 import BeautifulSoup
        r=requests.get("https://html.duckduckgo.com/html/",params={"q":query},headers={"User-Agent":"Mozilla/5.0"},timeout=15)
        soup=BeautifulSoup(r.text,"html.parser")
        out=[]
        for a in soup.select(".result__a")[:6]:
            parent=a.parent.parent if a.parent else None
            sn=parent.select_one(".result__snippet") if parent else None
            out.append({"title":a.get_text(" ",strip=True),"url":a.get("href",""),"snippet":sn.get_text(" ",strip=True) if sn else ""})
        return out
    except Exception as e:
        return [{"title":"Web search unavailable","url":"","snippet":str(e)}]

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
            # Translate provider safety-filter errors into a clear, actionable message.
            err_text = str(err).lower()
            if "nsfw" in err_text or '"code": 8007' in err_text or "'code': 8007" in err_text:
                return JSONResponse({
                    "error": "Cloudflare's image safety filter rejected this prompt. This can be a false positive. Try rephrasing it with neutral, specific visual details (subject, setting, style, lighting), and avoid ambiguous wording. Sambot cannot override the provider's safety filter.",
                    "code": "IMAGE_PROMPT_FILTERED",
                    "retryable": True
                }, status_code=400)
            if r.status_code == 429:
                return JSONResponse({"error":"Cloudflare image generation is rate-limited right now. Wait a little and try again.","code":"IMAGE_RATE_LIMITED","retryable":True},status_code=429)
            return JSONResponse({"error":f"Cloudflare image generation failed (HTTP {r.status_code}). Please try again later. Provider details: {str(err)[:400]}","code":"IMAGE_PROVIDER_ERROR","retryable":r.status_code >= 500},status_code=r.status_code)
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

class ToolRequest(BaseModel):
    text: str
    kind: str = "calculate"

@app.post("/api/tools/calculate")
def calculate_tool(req: ToolRequest):
    """Evaluate basic arithmetic safely without eval/exec."""
    import ast, operator, math
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
           ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
    try:
        tree = ast.parse(req.text, mode="eval")
        def calc(node):
            if isinstance(node, ast.Expression): return calc(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool): return node.value
            if isinstance(node, ast.UnaryOp) and type(node.op) in ops: return ops[type(node.op)](calc(node.operand))
            if isinstance(node, ast.BinOp) and type(node.op) in ops:
                left, right = calc(node.left), calc(node.right)
                if isinstance(node.op, ast.Pow) and abs(right) > 1000: raise ValueError("Exponent too large.")
                value = ops[type(node.op)](left, right)
                if not math.isfinite(float(value)) or abs(value) > 1e100: raise ValueError("Result is too large.")
                return value
            raise ValueError("Only basic arithmetic is supported: +, -, *, /, //, %, and powers.")
        value = calc(tree)
        return {"ok": True, "expression": req.text, "result": value}
    except Exception as exc:
        return JSONResponse({"ok":False,"error":str(exc)},status_code=400)

@app.post("/api/tools/analyze-csv")
async def analyze_csv(file: UploadFile = File(...)):
    """Analyze CSV values with Python's standard library; no code execution."""
    import csv, io, statistics, collections
    if not (file.filename or "").lower().endswith(".csv"):
        return JSONResponse({"error":"Please upload a .csv file."},status_code=400)
    raw=await file.read()
    if len(raw)>8*1024*1024:
        return JSONResponse({"error":"CSV is larger than 8 MB."},status_code=413)
    try:
        text=raw.decode("utf-8-sig")
        reader=csv.DictReader(io.StringIO(text))
        rows=list(reader)
        if not reader.fieldnames or not rows:
            return JSONResponse({"error":"CSV must contain a header row and at least one data row."},status_code=400)
        report={"filename":file.filename,"rows":len(rows),"columns":[]}
        for name in reader.fieldnames[:50]:
            vals=[(r.get(name) or "").strip() for r in rows]
            present=[v for v in vals if v]
            missing=len(vals)-len(present)
            numeric=[]
            for v in present:
                try: numeric.append(float(v.replace(",","")))
                except ValueError: pass
            col={"name":name,"missing":missing,"unique":len(set(present))}
            if present and len(numeric)==len(present):
                col.update({"type":"numeric","min":min(numeric),"max":max(numeric),"mean":statistics.fmean(numeric),"median":statistics.median(numeric)})
            else:
                col["type"]="categorical/text"
                col["top_values"]=[{"value":v,"count":n} for v,n in collections.Counter(present).most_common(5)]
            report["columns"].append(col)
        return {"ok":True,"report":report}
    except Exception as exc:
        return JSONResponse({"error":"Could not analyze CSV: "+str(exc)},status_code=400)

@app.get("/api/capabilities")
def capabilities():
    return {"app":"Sambot X","login_required":False,"capabilities":{
      "chat":["streaming","model_selection","custom_instructions","local_memory","regenerate","edit_messages"],
      "voice":["browser_speech_input","read_aloud","hands_free_voice_mode","language_and_speed_settings"],
      "media":["cloudflare_image_generation","vision_endpoint","file_uploads"],
      "tools":["web_search","safe_calculator","csv_statistics","markdown_export","json_import_export"],
      "storage":["browser_local_history","local_preferences"],
      "limitations":["no OpenAI private model access","no full Python execution sandbox","no cross-device sync without a server-side identity or shared profile","browser speech support varies"]
    }}

@app.post("/api/chat/stream")
def stream_chat(req: ChatRequest):
    import json
    from fastapi.responses import StreamingResponse
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return JSONResponse({"error": "GROQ_API_KEY is not configured in Render."}, status_code=503)
    messages = [{"role": m.role, "content": m.content} for m in req.messages if m.role in ("user", "assistant")][-20:]
    if not messages:
        return JSONResponse({"error": "No chat messages were sent."}, status_code=400)
    context = ""
    if req.web_search:
        results = web_search(messages[-1]["content"])
        context = "\n\nCURRENT WEB RESULTS:\n" + "\n".join(f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results)
    system = "You are Sambot X, a helpful AI assistant. Be accurate, clear, and honest. Use Markdown when useful."
    if req.memory:
        system += "\n\nUSER MEMORY:\n" + req.memory.strip()[:4000]
    if req.instructions:
        system += "\n\nUSER CUSTOM INSTRUCTIONS:\n" + req.instructions.strip()[:4000]
    model = req.model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    def events():
        try:
            stream = Groq(api_key=key, timeout=90.0, max_retries=1).chat.completions.create(
                model=model, messages=[{"role": "system", "content": system + context}] + messages,
                temperature=0.7, max_tokens=4000, stream=True)
            for chunk in stream:
                if chunk.choices:
                    piece = getattr(chunk.choices[0].delta, "content", None)
                    if piece:
                        yield "data: " + json.dumps({"token": piece}, ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"done": True, "model": model}) + "\n\n"
        except Exception as exc:
            print(f"SAMBOT_STREAM_ERROR: {type(exc).__name__}: {exc}")
            yield "data: " + json.dumps({"error": f"AI stream failed ({type(exc).__name__}): {exc}"}) + "\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.post("/api/chat")
def chat(req: ChatRequest):
    key=os.getenv("GROQ_API_KEY")
    if not key:
        print("SAMBOT_CHAT_ERROR: GROQ_API_KEY is not configured")
        return JSONResponse({"error":"GROQ_API_KEY is not configured in Render."},status_code=503)
    try:
        client=Groq(api_key=key, timeout=45.0, max_retries=1)
        messages=[{"role":m.role,"content":m.content} for m in req.messages if m.role in ("user","assistant")][-20:]
        if not messages:
            return JSONResponse({"error":"No chat messages were sent."},status_code=400)
        context=""
        if req.web_search:
            results=web_search(messages[-1]["content"])
            context="\\n\\nCURRENT WEB RESULTS:\\n"+"\\n".join(f"- {x['title']} | {x['url']} | {x['snippet']}" for x in results)
        system=("You are Sambot X, a helpful AI assistant. Be accurate, clear, and honest about limitations. "
                "Help with coding, writing, studying, math, planning, brainstorming, and general tasks. "
                "Use attached file contents when supplied. If web results are supplied, use them for current information and mention sources naturally.")
        result=client.chat.completions.create(
            model=os.getenv("GROQ_MODEL","openai/gpt-oss-120b"),
            messages=[{"role":"system","content":system+context}]+messages,
            temperature=0.7,
            max_tokens=1800,
        )
        reply=result.choices[0].message.content
        if not reply:
            print("SAMBOT_CHAT_ERROR: Groq returned an empty message")
            return JSONResponse({"error":"Groq returned an empty reply. Check GROQ_MODEL in Render."},status_code=502)
        print("SAMBOT_CHAT_OK: reply generated")
        return {"reply":reply}
    except Exception as e:
        print(f"SAMBOT_CHAT_ERROR: {type(e).__name__}: {e}")
        return JSONResponse({"error":f"AI request failed ({type(e).__name__}): {e}"},status_code=502)
