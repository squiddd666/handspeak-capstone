import('./app.js').catch(()=>{
 document.getElementById('status').textContent='The camera test could not load. Check your connection and reload the page.';
 document.getElementById('start').disabled=true;
});
