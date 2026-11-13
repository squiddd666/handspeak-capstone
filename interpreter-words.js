export function wordLogState(draft){
  const words=draft.trim().split(/\s+/).filter(Boolean);
  const current=draft&&!/\s$/.test(draft)?words.pop()||'':'';
  return {current,completed:words};
}
export function commitCurrentWord(draft){
  if(!wordLogState(draft).current)return draft;
  return draft.length<1000?draft+' ':null;
}
