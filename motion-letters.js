// Experimental temporal template matching. No stationary pose can emit J/Z.
function letterSequence(rows, tip, aspect=1){
  const scales=rows.map(r=>Math.hypot((r.points[5].x-r.points[17].x)*aspect,r.points[5].y-r.points[17].y));
  const scale=scales.reduce((a,b)=>a+b,0)/scales.length;
  if(!scale)return null;
  const first=rows[0].points[tip];
  const raw=rows.map(r=>{
    const p=r.points,w=p[0];
    return [(p[tip].x-first.x)*aspect/scale,(p[tip].y-first.y)/scale,
      ...[4,8,12,16,20].flatMap(i=>[(p[i].x-w.x)*aspect/scale,(p[i].y-w.y)/scale])];
  });
  const start=rows[0].t,span=rows[rows.length-1].t-start;
  if(span<=0)return null;
  return Array.from({length:24},(_,i)=>{
    const t=start+span*i/23;let j=1;while(j<rows.length-1&&rows[j].t<t)j++;
    const a=j-1,b=j,f=(t-rows[a].t)/(rows[b].t-rows[a].t||1);
    return raw[a].map((v,k)=>v+(raw[b][k]-v)*f);
  });
}

function hasZStrokes(sequence){
  let direction=0,extreme=sequence[0][0],strokes=0;
  for(const row of sequence){
    const x=row[0];
    if(!direction){if(Math.abs(x-extreme)>.3){direction=Math.sign(x-extreme);strokes=1;extreme=x;}}
    else if((x-extreme)*direction>=0)extreme=x;
    else if((extreme-x)*direction>.3){direction=-direction;strokes++;extreme=x;}
  }
  return strokes===3&&sequence[sequence.length-1][1]-sequence[0][1]>.25;
}

function hasJStroke(sequence){
  const xs=sequence.map(row=>row[0]),ys=sequence.map(row=>row[1]);
  const minimum=Math.min(...xs),minimumAt=xs.indexOf(minimum);
  const maximumY=Math.max(...ys);
  const finalX=xs[xs.length-1],finalY=ys[ys.length-1];
  return minimum<-.65
    && minimumAt>=2
    && finalX-minimum>.18
    && maximumY-ys[0]>.45
    && finalY-ys[minimumAt]>.1;
}

function startsAsPinkyPose(points,aspect=1){
  const scale=Math.hypot((points[5].x-points[17].x)*aspect,points[5].y-points[17].y)||1;
  const wrist=points[0];
  const distance=i=>Math.hypot((points[i].x-wrist.x)*aspect,points[i].y-wrist.y)/scale;
  return distance(20)>1.35&&Math.max(distance(8),distance(12),distance(16))<1.45;
}

export function createMotionLetters(){
  let templates=[],rows=[],lastAt=-Infinity,lastCheck=-Infinity,lockedUntil=-Infinity;
  function reset(){rows=[];lastAt=-Infinity;lastCheck=-Infinity;lockedUntil=-Infinity;}
  return {
    reset,
    setModel(model){
      templates=model?.version===1&&Array.isArray(model.templates)?model.templates.filter(t=>['J','Z'].includes(t.letter)&&t.tip===(t.letter==='J'?20:8)&&t.sequence?.length===24&&t.sequence.every(r=>r.length===12&&r.every(Number.isFinite))):[];
      const valid=templates.length===2&&new Set(templates.map(t=>t.letter)).size===2;
      if(!valid)templates=[];
      reset();return valid;
    },
    frame(points,now,aspect=1,stableMotionGate=false){
      if(!points||!Number.isFinite(now)){reset();return {moving:false,result:null};}
      if(now-lastAt>500||now<lastAt){rows=[];lastCheck=-Infinity;}
      if(now-lastAt<40)return {moving:false,result:null};
      lastAt=now;rows.push({points,t:now});rows=rows.filter(r=>now-r.t<=5000);
      const recent=rows.filter(r=>now-r.t<=500),first=recent[0]?.points;
      const span=Math.hypot((points[5].x-points[17].x)*aspect,points[5].y-points[17].y);
      // Opt-in: only the static-suppression gate uses this floor. Existing
      // J/Z trajectory normalization and template acceptance stay unchanged.
      const scale=(stableMotionGate?Math.max(span,.65*Math.hypot((points[9].x-points[0].x)*aspect,points[9].y-points[0].y)):span)||1;
      const moving=first&&[8,20].some(i=>Math.hypot((points[i].x-first[i].x)*aspect,points[i].y-first[i].y)/scale>.18);
      if(now<lockedUntil)return {moving:true,result:null};
      if(!templates.length||now-lastCheck<100)return {moving:!!moving,result:null};
      lastCheck=now;let best=null;
      for(let start=0;start<rows.length-3;start++){
        const duration=now-rows[start].t;if(duration<400||duration>4500)continue;
        if(rows.length-start<6)continue;
        for(const template of templates){
          const sequence=letterSequence(rows.slice(start),template.tip,aspect);if(!sequence)continue;
          const spread=Math.max(...sequence.map(r=>r[0]))-Math.min(...sequence.map(r=>r[0]))+Math.max(...sequence.map(r=>r[1]))-Math.min(...sequence.map(r=>r[1]));
          if(spread<.65)continue;
          // A downward sweep alone is not a completed J: require its rising hook.
          if(template.letter==='J'&&Math.max(...sequence.map(r=>r[1]))-sequence[sequence.length-1][1]<.12)continue;
          for(const mirror of [1,-1]){
            let motion=0,shape=0;
            sequence.forEach((r,i)=>r.forEach((v,k)=>{
              const d=v*(k%2===0?mirror:1)-template.sequence[i][k];
              if(k<2)motion+=d*d;else shape+=d*d;
            }));
            motion=Math.sqrt(motion/48);shape=Math.sqrt(shape/240);
            const score=motion+.25*shape;
            const closeTemplate=motion<.28&&shape<.75&&score<.38;
            const geometricJ=template.letter==='J'
              &&startsAsPinkyPose(rows[start].points,aspect)
              &&shape<.75
              &&hasJStroke(sequence.map(row=>row.map((v,k)=>k%2===0?v*mirror:v)));
            // Low-frame-rate Z may have uneven stroke timing; require all three
            // alternating strokes plus the index-handshape match, not just drift.
            const completeZ=template.letter==='Z'&&hasZStrokes(sequence)&&motion<.65&&shape<.6&&score<.75;
            if((closeTemplate||geometricJ||completeZ)&&(!best||score<best.score))best={letter:template.letter,score:geometricJ?Math.min(score,.36):score,duration,observations:rows.length-start};
          }
        }
      }
      if(best){rows=[];lockedUntil=now+1400;return {moving:true,result:{letter:best.letter,confidence:Math.max(0,1-best.score),source:'motion-letter',latencyMs:best.duration,observationCount:best.observations}};}
      return {moving:!!moving,result:null};
    }
  };
}

export {letterSequence};

// Separate temporal state for each observed hand prevents a resting hand or
// a left/right switch from being spliced into another hand's J/Z trajectory.
export function createMultiHandMotionLetters(){
  let model=null,tracks=[],nextId=1;
  const distance=(a,b,aspect)=>Math.hypot((a[0].x-b[0].x)*aspect,a[0].y-b[0].y);
  const scale=(p,aspect)=>Math.max(Math.hypot((p[5].x-p[17].x)*aspect,p[5].y-p[17].y),.65*Math.hypot((p[0].x-p[9].x)*aspect,p[0].y-p[9].y),.01);
  return {
    reset(){tracks=[];},
    setModel(value){const check=createMotionLetters();if(!check.setModel(value)){model=null;tracks=[];return false;}model=value;tracks=[];return true;},
    frame(hands,now,aspect=1,stableMotionGate=false){
      if(!Array.isArray(hands)||!hands.length){tracks=[];return {moving:false,result:null,presentIds:[]};}
      if(!Array.isArray(hands[0]))hands=[hands];
      const previous=tracks.filter(t=>now>=t.at&&now-t.at<=500),used=new Set(),next=[],results=[];let moving=false;
      for(const points of hands){
        const candidates=previous.filter(t=>!used.has(t.id)).map(t=>({track:t,d:distance(points,t.points,aspect)/Math.max(scale(points,aspect),scale(t.points,aspect))})).sort((a,b)=>a.d-b.d);
        let track=candidates[0]?.d<2?candidates[0].track:null;
        if(!track){const matcher=createMotionLetters();if(model)matcher.setModel(model);track={id:nextId++,matcher};}
        used.add(track.id);track.points=points;track.at=now;next.push(track);
        const r=track.matcher.frame(points,now,aspect,stableMotionGate);moving=Boolean(r.moving)||moving;
        if(r.result)results.push({...r.result,handId:track.id});
      }
      tracks=next;return {moving,result:results.length===1?results[0]:null,presentIds:tracks.map(t=>t.id)};
    }
  };
}
