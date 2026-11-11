const $ = s => document.querySelector(s);
let user = null, mode = 'login', linkToken = '';
const dialog = $('#accountDialog');
async function api(path, data) {
  const response = await fetch(path, data ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)} : {});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed');
  return result;
}
function setMode(next) {
  mode = next;
  $('#accountForm').reset();
  $('#accountError').textContent = '';
  $('#accountTitle').textContent = {login:'Welcome back',register:'Create your account',setup:'Create the administrator account',password:'Change your password',reset:'Set a new password'}[mode];
  $('#accountEmailGroup').hidden = ['password','reset'].includes(mode);
  $('#accountEmail').required = !$('#accountEmailGroup').hidden;
  $('#accountEmail').type = mode === 'login' ? 'text' : 'email';
  $('#accountEmailGroup').firstChild.textContent = mode === 'login' ? 'Username or email' : 'Email';
  $('#currentPasswordGroup').hidden = mode !== 'password';
  $('#currentPassword').required = mode === 'password';
  $('#accountPassword').autocomplete = mode === 'login' ? 'current-password' : 'new-password';
  $('#accountPassword').minLength = mode === 'login' ? 1 : 12;
  $('#accountConfirmGroup').hidden = mode === 'login';
  $('#accountConfirm').required = mode !== 'login';
  $('#accountSubmit').textContent = {login:'Sign in',register:'Create account',setup:'Create administrator',password:'Save password',reset:'Reset password'}[mode];
  $('#accountSwitch').hidden = document.body.dataset.adminAccess === 'true' || !['login','register'].includes(mode);
  $('#accountSwitch').textContent = mode === 'login' ? 'New here? Create an account' : 'Already registered? Sign in';
  $('#accountHelp').textContent = mode === 'login' ? 'Forgot your password? Ask the site administrator for a password-reset link.' : 'Use 12–128 characters. Your email is your sign-in name; email delivery is not configured.';
}
function show(next='login') { setMode(next); dialog.showModal(); }
async function refresh() {
  try {
    user = (await api('/api/auth/me')).user;
    $('#accountButton').textContent = user ? 'Account' : 'Sign in';
    $('#accountSummary').hidden = !user;
    $('#accountIdentity').textContent = user?.email || '';
    $('#adminLink').hidden = user?.role !== 'admin';
    $('#historyPrivacy').textContent = user ? 'Your saved messages are linked to your account. Sign in on another device to access them.' : 'Guest history is private to this browser cookie. Sign in to keep it with an account. Clearing cookies removes your access to guest history.';
    window.dispatchEvent(new CustomEvent('handspeak-auth-changed',{detail:{user}}));
  } catch { $('#accountError').textContent = 'Account service is unavailable. Please try again.'; }
}
$('#accountButton').addEventListener('click',()=>{
  if (user) { $('#accountSummary').scrollIntoView({behavior:'smooth',block:'center'}); $('#changePasswordButton').focus({preventScroll:true}); }
  else show();
});
$('#accountClose').addEventListener('click',()=>dialog.close());
$('#accountSwitch').addEventListener('click',()=>setMode(mode==='login'?'register':'login'));
$('#changePasswordButton').addEventListener('click',()=>show('password'));
$('#signOutButton').addEventListener('click',async()=>{
  try { await api('/api/auth/logout',{}); await refresh(); $('#accountNotice').textContent='Signed out.'; }
  catch (error) { $('#accountNotice').textContent=error.message; }
});
$('#accountForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const password=$('#accountPassword').value;
  if (mode!=='login' && password!==$('#accountConfirm').value) { $('#accountError').textContent='The passwords do not match.'; return; }
  $('#accountSubmit').disabled=true;
  try {
    await api('/api/auth/'+mode,{email:$('#accountEmail').value,password,currentPassword:$('#currentPassword').value,token:linkToken});
    if (mode==='reset') { setMode('login'); $('#accountError').textContent='Password reset. Sign in with your new password.'; linkToken=''; await refresh(); }
    else { dialog.close(); $('#accountForm').reset(); await refresh(); $('#accountNotice').textContent=mode==='password'?'Password updated. Other devices were signed out.':'Signed in. Your saved messages are ready.'; }
  } catch(error) { $('#accountError').textContent=error.message; }
  finally { $('#accountSubmit').disabled=false; }
});
// Bootstrap/reset secrets stay in the fragment, never sent in page URLs or referrers.
function handleAccountLink() {
  const fragment=new URLSearchParams(location.hash.slice(1));
  if (fragment.has('setup') || fragment.has('reset')) {
    const next=fragment.has('setup')?'setup':'reset'; linkToken=fragment.get(next);
    history.replaceState(null,'',location.pathname+location.search);
    if (dialog.open) dialog.close();
    show(next);
  }
}
window.addEventListener('hashchange',handleAccountLink);
handleAccountLink();
if(new URLSearchParams(location.search).has('signin')) { show('login'); $('#accountHelp').textContent='Sign in as an administrator, then open Admin dashboard → phpMyAdmin.'; }
void refresh();
