WEB_APP_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Change2MD — Convert to Markdown</title>
  <meta name="description" content="Convert a file or public webpage to Markdown for any AI chat or model.">
  <style>
    :root{color-scheme:light;--bg:#f5f3ed;--surface:#fffdf8;--ink:#20211f;--muted:#686b64;--line:#d8d6cc;--accent:#536b45}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,sans-serif}
    main{width:min(880px,calc(100% - 32px));margin:0 auto;padding:48px 0}header{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:56px}
    header a{color:var(--ink);text-decoration:none;font-weight:650}.eyebrow{font:12px/1.4 ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
    h1{font:700 clamp(36px,7vw,64px)/1.03 Georgia,serif;letter-spacing:-.035em;margin:12px 0 20px;max-width:760px}.lede{color:var(--muted);max-width:650px;font-size:18px}
    form,section.output{background:var(--surface);border:1px solid var(--line);padding:24px;margin-top:32px}label{display:block;font-weight:650;margin:20px 0 8px}label:first-child{margin-top:0}
    input{width:100%;min-height:48px;border:1px solid var(--line);background:#fff;padding:12px;color:var(--ink);font:inherit}input:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
    .hint{color:var(--muted);font-size:14px;margin:8px 0 0}.actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}button{min-height:46px;border:1px solid var(--accent);background:var(--accent);color:#fff;padding:10px 18px;font:650 14px system-ui;cursor:pointer}button.secondary{background:transparent;color:var(--accent)}button:disabled{opacity:.5;cursor:wait}
    #status{margin-top:16px;color:var(--accent)}#status.error{color:#a13d35}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:480px;overflow:auto;background:#f0eee7;padding:20px;font:14px/1.6 ui-monospace,monospace}
    [hidden]{display:none!important}footer{margin-top:32px;color:var(--muted);font-size:14px}code{font-family:ui-monospace,monospace}
    @media(max-width:520px){main{padding:28px 0}header{margin-bottom:36px}form,section.output{padding:18px}}
  </style>
</head>
<body><main>
  <header><a href="/convert">Change2MD</a><a href="https://github.com/UtpalDasLabs/change2md">GitHub</a></header>
  <p class="eyebrow">Universal AI input converter</p>
  <h1>Turn a file or webpage into Markdown.</h1>
  <p class="lede">Use it with any AI chat, harness or model. Choose one source, convert it, then copy or download the result.</p>
  <form id="convert-form">
    <label for="file">Upload a file</label>
    <input id="file" name="file" type="file">
    <p class="hint">PDF, Office documents, HTML, CSV, JSON, XML, EPUB, ZIP, text and other MarkItDown-supported inputs. Maximum 25 MB.</p>
    <label for="url">Or convert a public webpage</label>
    <input id="url" name="url" type="url" inputmode="url" placeholder="https://example.com" autocomplete="url">
    <p class="hint">The URL must use public HTTPS. Login-protected and private-network pages are not supported.</p>
    <div class="actions"><button id="submit" type="submit">Convert to Markdown</button></div>
    <p id="status" role="status" aria-live="polite"></p>
  </form>
  <section class="output" id="output-section" aria-labelledby="output-title" hidden>
    <h2 id="output-title">Markdown</h2>
    <pre id="output" tabindex="0"></pre>
    <div class="actions">
      <button id="copy" class="secondary" type="button">Copy Markdown</button>
      <button id="download" class="secondary" type="button">Download Markdown</button>
      <button id="next" class="secondary" type="button" hidden>Load next chunk</button>
    </div>
    <p id="chunk-info" class="hint"></p>
  </section>
  <footer>Cloud conversion is temporary and files are deleted after the request. For sensitive documents, use the <a href="https://github.com/UtpalDasLabs/change2md/blob/main/LOCAL.md">Local edition</a>.</footer>
</main>
<script>
const form=document.getElementById('convert-form'),file=document.getElementById('file'),url=document.getElementById('url');
const submit=document.getElementById('submit'),next=document.getElementById('next'),status=document.getElementById('status');
const section=document.getElementById('output-section'),output=document.getElementById('output'),info=document.getElementById('chunk-info');
let nextOffset=0,sourceUrl='';
function busy(value){submit.disabled=value;next.disabled=value;submit.textContent=value?'Converting…':'Convert to Markdown'}
function showError(message){status.textContent=message;status.className='error';busy(false)}
async function convert(append=false){
  const selected=file.files[0],enteredUrl=url.value.trim();
  if(!append&&!selected&&!enteredUrl)return showError('Choose a file or enter a public HTTPS URL.');
  if(!append&&selected&&enteredUrl)return showError('Choose either a file or a URL, not both.');
  busy(true);status.className='';status.textContent=append?'Loading the next chunk…':'Converting…';
  try{
    const offset=append?nextOffset:0;let response;
    if(selected){const data=new FormData();data.append('file',selected);data.append('offset',offset);data.append('max_chars','200000');response=await fetch('/api/convert/file',{method:'POST',body:data})}
    else{sourceUrl=enteredUrl||sourceUrl;response=await fetch('/api/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:sourceUrl,offset,max_chars:200000})})}
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Conversion failed.');
    output.textContent=append?output.textContent+'\n'+data.markdown:data.markdown;
    nextOffset=data.next_offset||0;next.hidden=!data.has_more;section.hidden=false;
    info.textContent=`Showing ${data.total_chars.toLocaleString()} total characters${data.has_more?'; more chunks are available':''}.`;
    status.textContent=data.has_more?'Chunk ready. Load the next chunk or use the current Markdown.':'Markdown ready.';
    if(!append)section.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
  }catch(error){showError(error.message||'Conversion failed. Check the source and try again.')}finally{busy(false)}
}
form.addEventListener('submit',event=>{event.preventDefault();convert(false)});next.addEventListener('click',()=>convert(true));
document.getElementById('copy').addEventListener('click',async()=>{await navigator.clipboard.writeText(output.textContent);status.textContent='Markdown copied.'});
document.getElementById('download').addEventListener('click',()=>{const blob=new Blob([output.textContent],{type:'text/markdown;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(file.files[0]?.name.replace(/\.[^.]+$/,'')||'change2md')+'.md';a.click();URL.revokeObjectURL(a.href)});
</script>
</body></html>'''
