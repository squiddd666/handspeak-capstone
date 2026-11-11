// Preserve administrator setup/reset links without a public account interface.
const fragment=new URLSearchParams(location.hash.slice(1));
if(new URLSearchParams(location.search).has('signin')||fragment.has('setup')||fragment.has('reset')){
  location.replace('account.html?signin=1'+location.hash);
}else{
  // Existing account sessions retain access; no automatic logout or data migration.
  fetch('/api/auth/me').then(response=>response.ok?response.json():null).then(data=>{
    if(data?.user)document.querySelector('#historyPrivacy').textContent='Saved history is private to your existing account session.';
  }).catch(()=>{});
}
