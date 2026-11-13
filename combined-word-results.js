// Scores from these models are not calibrated against each other. Never rank across models.
export function combineWordResults(browser,openhands){
 const results=new Map();
 for(const [name,result] of [['Browser',browser],['OpenHands',openhands]]){
  if(!result?.label)continue;
  const word=result.label.trim().toUpperCase();
  const entry=results.get(word)||{word,sources:[],confidence:null};
  entry.sources.push(name);
  if(name==='OpenHands'&&Number.isFinite(result.confidence))entry.confidence=result.confidence;
  results.set(word,entry);
 }
 return [...results.values()];
}
