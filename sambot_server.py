"""Render entry point for Sambot X, including optional feature routes."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import web_app
from web_app import app
from sambot_features import router as features_router

app.include_router(features_router)

# Add a small model picker and image-analysis control to the existing interface
# without replacing the desktop app or the existing chat API.
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
  const topbar = document.querySelector('.topbar > div:first-child');
  if (topbar) {
    const select = document.createElement('select');
    select.id = 'sambotModelPicker';
    select.title = 'Choose the chat model';
    select.style.cssText = 'margin-left:10px;max-width:190px;background:#15181e;color:inherit;border:1px solid #343842;border-radius:8px;padding:7px;font-size:12px';
    select.innerHTML = '<option>Loading models…</option>';
    topbar.appendChild(select);
    fetch('/api/models').then(r=>r.json()).then(data=>{
      select.innerHTML = '';
      (data.models||[]).forEach(m=>{
        const o=document.createElement('option');o.value=m.id;o.textContent=m.name;select.appendChild(o);
      });
      select.value=localStorage.getItem('sambot_model')||data.default;
      if(!select.value && select.options.length)select.selectedIndex=0;
    }).catch(()=>{select.innerHTML='<option value="openai/gpt-oss-120b">Default model</option>'});
    select.addEventListener('change',()=>localStorage.setItem('sambot_model',select.value));
  }
  const tools = document.querySelector('.composer .tools');
  if (tools) {
    const imageBtn = document.createElement('button');
    imageBtn.className='toolbtn'; imageBtn.textContent='🖼 Analyze image';
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
          const r=await fetch('/api/vision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,image_data_url:reader.result})});
          const j=await r.json();
          const rows=document.querySelectorAll('#chat .row.assistant');
          const last=rows[rows.length-1];
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
    for route in app.router.routes:
        if getattr(route, "path", None) == "/" and "GET" in getattr(route, "methods", set()):
            route.endpoint = enhanced_home
            route.response_class = HTMLResponse
            break
