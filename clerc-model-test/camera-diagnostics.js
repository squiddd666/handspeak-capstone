// Opt-in, aggregate-only camera diagnostics. No pixels or landmarks are retained.
export function createCameraDiagnostics({clock=()=>performance.now()}={}) {
  const started=clock(), samples=[], events=[];
  let lastVideoTime=-1, lastFrameAt=0, rendered=0, processed=0, skipped=0;
  const add=(type,extra={})=>events.push({type,t_ms:Math.round(clock()-started),...extra});
  return {
    frame({videoTime,at=clock(),latencyMs=0,hands=0,pose=false,motion=null,processedFrame=true}) {
      rendered++;
      if (!processedFrame || videoTime===lastVideoTime) {skipped++;return false;}
      const dt=lastFrameAt ? at-lastFrameAt : null;
      processed++;lastFrameAt=at;lastVideoTime=videoTime;
      samples.push({t_ms:Math.round(at-started),video_time_ms:Math.round(videoTime*1000),dt_ms:dt===null?null:Math.round(dt),latency_ms:Math.round(latencyMs),hands:Math.min(2,hands),pose:!!pose,motion:motion===null?null:Number(motion.toFixed(4))});
      return true;
    },
    event:add,
    report({sourceDurationMs=null}={}) {
      const elapsed=Math.max(1,clock()-started), n=samples.length;
      return {schema:1,elapsed_ms:Math.round(elapsed),source_duration_ms:sourceDurationMs,rendered_callbacks:rendered,processed_frames:processed,skipped_callbacks:skipped,processing_fps:Number((processed*1000/elapsed).toFixed(2)),hand_detection_rate:n?samples.filter(x=>x.hands>0).length/n:0,pose_detection_rate:n?samples.filter(x=>x.pose).length/n:0,mean_detector_latency_ms:n?samples.reduce((a,x)=>a+x.latency_ms,0)/n:0,samples:[...samples],events:[...events]};
    }
  };
}
