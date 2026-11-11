const $=s=>document.querySelector(s);let data=null;
const text=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e;};
async function api(path,body){const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;}
function selection(){const id=$('#adminWord').value,entry=data?.vocabulary.find(item=>item.id===id),settings=data?.settings[id]||{};$('#adminWordDescription').value=settings.description||'';$('#adminWordDescription').placeholder=entry?.note||'Add a learning description…';$('#adminWordVideo').value=settings.video||'';$('#adminWordHidden').checked=Boolean(settings.hidden);}
async function load(){
 try{
  data=await api('/api/admin/experience');const current=$('#adminWord').value;$('#adminWord').replaceChildren(...data.vocabulary.map(item=>new Option(item.label,item.id)));if(data.vocabulary.some(item=>item.id===current))$('#adminWord').value=current;
  $('#adminWordVideo').replaceChildren(new Option('Use the original lesson/video',''),...data.videos.map(path=>new Option(path.split('/').pop(),path)));selection();
  $('#adminServiceStatus').textContent=`Local LLM: ${data.llm.available?(data.llm.warming?'warming up':'available'):'unavailable'} (${data.llm.model||'not configured'}). Published category models: ${data.models.map(pack=>pack.name).join(', ')||'none'}. Camera detection runs in the visitor’s browser; this is not a camera accuracy check.`;
  const container=$('#adminWordFeedback');container.replaceChildren();if(!data.feedback.length)container.append(text('p','No word feedback yet.'));
  for(const item of data.feedback){
   const row=document.createElement('article');row.className='feedback-item';row.append(text('strong',`${item.predicted} → ${item.expected}`),text('p',`${item.verdict} · ${item.status} · ${item.model}`),text('small',new Date(item.created_at).toLocaleString()));
   const actions=document.createElement('div');actions.className='admin-feedback-actions';for(const status of ['reviewed','dismissed']){const button=text('button',status==='reviewed'?'Mark reviewed':'Dismiss');button.type='button';button.className='text-button';button.disabled=item.status===status;button.onclick=async()=>{button.disabled=true;try{await api('/api/admin/match-feedback',{id:item.id,status});await load();}catch(error){$('#adminServiceStatus').textContent=error.message;button.disabled=false;}};actions.append(button);}row.append(actions);container.append(row);
  }
 }catch(error){$('#adminServiceStatus').textContent=error.message;}
}
$('#adminWord').onchange=selection;
$('#adminWordForm').onsubmit=async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{await api('/api/admin/vocabulary-settings',{id:$('#adminWord').value,description:$('#adminWordDescription').value,video:$('#adminWordVideo').value,hidden:$('#adminWordHidden').checked});$('#adminWordStatus').textContent='Saved. Refresh public pages to see the change.';await load();}catch(error){$('#adminWordStatus').textContent=error.message;}finally{button.disabled=false;}};
$('#adminVideoForm').onsubmit=async event=>{
 event.preventDefault();const file=$('#adminVideoFile').files[0];if(!file)return;if(file.size>20*1024*1024){$('#adminWordStatus').textContent='Choose an MP4 up to 20 MiB.';return;}
 $('#adminUploadVideo').disabled=true;$('#adminWordStatus').textContent='Uploading and checking the practice video…';
 try{const response=await fetch('/api/admin/practice-video?id='+encodeURIComponent($('#adminWord').value),{method:'POST',headers:{'Content-Type':'video/mp4'},body:file});const result=await response.json();if(!response.ok)throw Error(result.error);$('#adminWordStatus').textContent='Video uploaded and assigned. Refresh public pages to view it.';$('#adminVideoForm').reset();await load();}catch(error){$('#adminWordStatus').textContent=error.message||'Upload failed.';}finally{$('#adminUploadVideo').disabled=false;}
};
$('#adminExperienceRefresh').onclick=load;
$('#adminRefresh').addEventListener('click',()=>void load());
void load();
