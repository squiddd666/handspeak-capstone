let settings={},promise;
export function loadVocabularySettings(){
 return promise??=fetch('/api/vocabulary-settings',{cache:'no-store',signal:AbortSignal.timeout(5000)}).then(r=>r.ok?r.json():null).then(data=>{
  settings=data?.items||{};document.dispatchEvent(new CustomEvent('handspeak:vocabulary-settings'));return settings;
 }).catch(()=>settings);
}
export const wordSettings=id=>settings[id]||{};
export const isWordEnabled=label=>!Object.values(settings).some(item=>item.hidden&&item.label===label);
export function applyVocabularySettings(items){return items.filter(item=>!wordSettings(item.id).hidden).map(item=>({...item,note:wordSettings(item.id).description||item.note,video:wordSettings(item.id).video||item.video}));}
void loadVocabularySettings();
