const $=s=>document.querySelector(s);
async function api(path,data){const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const body=await r.json();if(!r.ok)throw new Error(body.error||'Request failed');return body;}
function text(tag,value){const el=document.createElement(tag);el.textContent=value;return el;}
async function load(){
  $('#adminRefresh').disabled=true;
  try {
    const data=await api('/api/admin/overview?q='+encodeURIComponent($('#adminSearchEmail').value.trim()));$('#databaseStatus').textContent=`Connected database: ${data.database.engine}. Accounts, messages, and feedback are saved here.`;$('#databaseManageLink').hidden=!data.database.managementUrl;$('#adminContent').hidden=false;$('#adminStatus').textContent='Signed in as an administrator.';
    $('#adminTotals').replaceChildren();
    for(const [key,label] of [['users','Accounts'],['activeUsers','Active accounts'],['sessions','Saved messages'],['evaluations','Feedback responses']]){const tile=document.createElement('div');tile.append(text('b',data.totals[key]),text('span',label));$('#adminTotals').append(tile);}
    $('#adminUsers').replaceChildren();
    for(const user of data.users){const card=document.createElement('article');card.className='admin-user';card.append(text('strong',user.email),text('p',`${user.role} · ${user.active?'Active':'Inactive'} · ${user.saved_sessions} saved messages`));
      if(user.role!=='admin'){const toggle=text('button',user.active?'Deactivate':'Activate');toggle.className='secondary-button';toggle.onclick=async()=>{toggle.disabled=true;try{await api('/api/admin/user-status',{userId:user.id,active:!user.active});await load();}catch(e){$('#adminStatus').textContent=e.message;toggle.disabled=false;}};card.append(toggle);}
      const reset=text('button','Create reset link');reset.className='text-button';reset.disabled=!user.active;reset.onclick=async()=>{reset.disabled=true;try{const result=await api('/api/admin/reset-link',{userId:user.id});$('#resetLinkGroup').hidden=false;$('#resetLink').value=location.origin+'/#reset='+result.token;$('#resetLinkStatus').textContent=`Reset link for ${user.email}. Expires in ${result.expiresInMinutes} minutes.`;}catch(e){$('#adminStatus').textContent=e.message;}finally{reset.disabled=!user.active;}};card.append(reset);$('#adminUsers').append(card);
    }
    $('#adminFeedback').replaceChildren();
    if(!data.evaluations.length)$('#adminFeedback').append(text('p','No feedback yet.'));
    for(const item of data.evaluations){const card=document.createElement('article');card.className='feedback-item';card.append(text('strong',item.respondent_type),text('p',`Accuracy ${item.accuracy}/5 · Usability ${item.usability}/5 · Performance ${item.performance}/5`),text('p',item.comments||'No comment'),text('small',new Date(item.created_at).toLocaleString()));$('#adminFeedback').append(card);}
  }catch(e){$('#adminContent').hidden=true;$('#adminStatus').textContent=e.message+'. Use Administrator sign in above to continue.';}
  finally{$('#adminRefresh').disabled=false;}
}
$('#adminRefresh').onclick=load;
$('#adminSearch').onsubmit=event=>{event.preventDefault();void load();};
$('#copyResetLink').onclick=async()=>{try{await navigator.clipboard.writeText($('#resetLink').value);$('#resetLinkStatus').textContent='Copied. Share privately with the account owner.';}catch{$('#resetLink').select();$('#resetLinkStatus').textContent='Select and copy the link manually.';}};
void load();

window.addEventListener('focus',()=>{void load();});
