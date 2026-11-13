const $=s=>document.querySelector(s);
const views={home:['home'],workspace:['workspace'],learn:['learn','motion-studio'],'ai-studio':['ai-studio'],history:['history'],evaluate:['evaluate'],about:['about']};
const lesson=$('#sign-examples'),lessonHome=document.createComment('Lesson position');lesson.before(lessonHome);
let current='';
function show(target,update=true){
 const node=document.getElementById(target.replace(/^#/,''));
 let view=Object.keys(views).find(v=>views[v].some(id=>document.getElementById(id)?.contains(node)))||'home';
 if(target==='#sign-examples')view='learn';
 if(view!=='workspace'&&$('#cameraLesson').contains(lesson)){lessonHome.after(lesson);$('#cameraLesson').hidden=true;}
 for(const [key,ids] of Object.entries(views))for(const id of ids)document.getElementById(id).hidden=key!==view;
 document.querySelector('.application-help').hidden=view!=='about';
 for(const link of document.querySelectorAll('.site-header nav a')){const active=link.hash==='#'+view;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 if(current!==view)document.dispatchEvent(new CustomEvent('handspeak:view',{detail:{view}}));
 current=view;if(update&&location.hash!==target)history.pushState(null,'',target);
}
document.addEventListener('handspeak:navigate',e=>show(e.detail.target));
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#"]');if(!a)return;const target=a.hash||'#home';if(target==='#main')return;show(target);},true);
window.addEventListener('popstate',()=>show(location.hash||'#workspace',false));
window.addEventListener('hashchange',()=>show(location.hash||'#workspace',false));
$('#startSigning').addEventListener('click',()=>show('#workspace'));
function dock(){show('#workspace');$('#cameraLesson').hidden=false;$('#cameraLesson').append(lesson);}
function selectLesson(id){const button=words.find(b=>b.dataset.signExample===id);if(button){button.click();$('#practiceWord').value=id;$('#practiceInstructions').textContent=$('#signExampleMode').textContent;}}
document.addEventListener('handspeak:default-practice',e=>{selectLesson(e.detail.label.toLowerCase().replaceAll(' ','-'));dock();});
document.addEventListener('handspeak:practice',e=>{selectLesson(e.detail.id);dock();});
document.addEventListener('handspeak:enable-word-preview',e=>{if(e.detail?.id){selectLesson(e.detail.id);dock();}else show('#workspace');});
const words=[...document.querySelectorAll('[data-sign-example]')];
for(const b of words)$('#practiceWord').add(new Option(b.textContent,b.dataset.signExample));
$('#preparePractice').addEventListener('click',()=>{
 const id=$('#practiceWord').value,button=words.find(b=>b.dataset.signExample===id);
 if(!button){$('#practiceInstructions').textContent='Choose a word first.';return;}
 button.click();dock();
 $('#signExamplePractice').click();
 $('#practiceInstructions').textContent='Automatic capture · Start the camera, sign once, then pause. Review the suggested word. If capture misses your movement, use Record a word.';
});
// Keep the LLM comparison next to the editable message and speech controls.
const interpreter=$('#interpretTitle').closest('section');$('#messageBox').closest('article').append(interpreter);
document.body.classList.remove('simple-mode');
const initialTarget=location.hash||'#workspace';
if(!location.hash)history.replaceState(null,'','#workspace');
show(initialTarget,false);
