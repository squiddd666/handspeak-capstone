let profilesPromise;
export function validAccuracy(metrics){
  return Boolean(metrics&&Number.isInteger(metrics.correct)&&Number.isInteger(metrics.total)&&metrics.total>0&&metrics.correct>=0&&metrics.correct<=metrics.total);
}
export function accuracyText(metrics){
  if(!validAccuracy(metrics))return 'Recorded accuracy: Not measured';
  const percent=(100*metrics.correct/metrics.total).toFixed(1).replace(/\.0$/,'');
  return `Recorded accuracy: ${percent}% (${metrics.correct}/${metrics.total} clips)`;
}
export function referenceAccuracy(profiles,label){
  for(const name of ['default','expanded','daily','baby']){
    const profile=profiles[name],metrics=profile?.words?.[label];
    if(validAccuracy(metrics))return {...metrics,model:profile.model,scope:profile.scope};
  }
  return null;
}
export function publishedAccuracy(pack,label){
  if(!pack?.labels?.includes(label))return null;
  const metrics=pack.test?.perWord?.[label]||(pack.labels.length===1?pack.test:null);
  return validAccuracy(metrics)?{...metrics,model:`${pack.name} preview`,scope:'Fresh recorded clips; live-camera accuracy unverified.'}:null;
}
export function loadAccuracyProfiles(){
  return profilesPromise??=fetch('models/motion-word-accuracy.json',{cache:'no-store'})
    .then(response=>response.ok?response.json():null)
    .then(data=>data?.version===1&&data.profiles?data.profiles:{})
    .catch(()=>({}));
}
