// Browser counterpart of training/catalog/motion_window.py; evaluation only.
export function alignTemporalWindow(row){
  const visible=row.rawFrames.map((f,i)=>f.some(h=>h!==null)?i:-1).filter(i=>i>=0);
  if(!visible.length)return row;
  let start=visible[0],end=visible.at(-1)+1;
  let frames=row.rawFrames.slice(start,end).map(f=>f.map(h=>h&&h.map(p=>({...p}))));
  let body=(row.body||row.rawFrames.map(()=>null)).slice(start,end);
  if(body.length!==frames.length)throw Error('Body and hands are not aligned');
  for(let side=0;side<2;side++){
    let i=1;
    while(i<frames.length-1){
      if(frames[i][side]!==null||frames[i-1][side]===null){i++;continue;}
      let next=i;while(next<frames.length&&frames[next][side]===null)next++;
      if(next===frames.length||next-i>2){i++;continue;}
      const a=frames[i-1][side],b=frames[next][side];
      for(let j=i;j<next;j++){
        const t=(j-i+1)/(next-i+1);
        frames[j][side]=a.map((p,k)=>Object.fromEntries(['x','y','z'].map(c=>[c,p[c]+(b[k][c]-p[c])*t])));
      }
      i=next+1;
    }
  }
  const runs=[];
  frames.forEach((f,i)=>{
    if(!f.some(h=>h!==null))return;
    if(!runs.length||i-runs.at(-1).end>3)runs.push({start:i,end:i,count:0});
    runs.at(-1).end=i;runs.at(-1).count++;
  });
  const strongest=runs.reduce((a,b)=>b.count>a.count?b:a);
  if(strongest.count>=8&&strongest.count>=.7*runs.reduce((s,r)=>s+r.count,0)){
    frames=frames.slice(strongest.start,strongest.end+1);body=body.slice(strongest.start,strongest.end+1);
    start+=strongest.start;end=start+frames.length;
  }
  return {...row,rawFrames:frames,body,temporalWindow:[start,end],...(row.timestamps?{timestamps:row.timestamps.slice(start,end)}:{})};
}
