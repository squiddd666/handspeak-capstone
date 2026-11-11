"""Report only the actual V6 validation/virtual-camera run and local test results."""
import json, re, statistics
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cache=ROOT.parent/'handspeak-training'
run=cache/'virtual-v6-validation'
def read(path,default):
    return json.loads(path.read_text()) if path.exists() else default
data=read(run/'results.json',{})
rows=data.get('results',[])
assert all(r['split']=='val' for r in rows)
assert len({r['source_sha256'] for r in rows})==len(rows)
responses=[r['backend_response'] for r in rows if r.get('backend_response')]
encoded=[r['experimentalEncoder'] for r in responses if r.get('experimentalEncoder',{}).get('state')=='encoded']
encoder_states=Counter(r.get('experimentalEncoder',{}).get('state','missing') for r in responses)
v3=Counter(r.get('state','missing') for r in responses)
def write(name,s):
    (ROOT/f'target20_v6_{name}.md').write_text(s.strip()+'\n',encoding='utf-8')
write('encoder_report',"""
# Target-20 V6 mask-aware encoder

Implemented in target20_encoder_v6.py as target20-mask-time-v6. V3 tensors, inference, threshold, and checkpoints are unchanged. V6 has no compatible trained model. Feeding its representation to V3 would be invalid.

Legacy issue: the motion-peak crop sees differences between a real hand coordinate and zero before masking. V6 instead trims only idle edges using the union of observed hand timestamps; it does not infer sign completion or crop on a motion peak. Coordinates use median shoulder midpoint and shoulder span to keep them body-relative without per-frame normalization jitter. Left/right visibility is independent. XY, visibility, velocity, and velocity validity are explicit arrays; an invalid zero is padding, never an observation.

A visibility break or a source gap over 200 ms starts a new segment. Interpolation and velocities stay within a single segment, even when the gap lies between adjacent output samples. Source timestamps remain intact. The encoder rejects malformed landmarks, duplicate or backward timestamps, degenerate shoulder scale, fewer than 8 visible-hand frames, insufficient active interval continuity, and sparse resampled support. These are engineering guards, not a classifier gate or a trained optimum.

In local opt-in QA, HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1 appends only an aggregate encoder status to existing Target-20 API responses. The frontend's real captured payload is used; no alternate V6 prediction is returned. Capture failures, encoder rejects, and V3 model outcomes are distinct.
""")
gaps=[e['max_source_gap_ms'] for e in encoded]
write('timestamp_audit',f"""
# Target-20 V6 timestamp audit

Browser capture uses the video source clock, not callback completion time. V6 accepts strictly increasing finite numeric milliseconds and retains original times; it produces a uniform 32-step grid within the observed hand span. Velocities are normalized coordinate units per second. Source gaps over 200 ms are not interpolated; timestamps are not fabricated. Dropped frames up to the gap bound are interpolated only within a contiguous visible run. Processing delay can still reduce frame coverage even when timestamps are correct.

Validation browser encodings: {len(encoded)}. Median of the maximum gap per encoded clip: {round(statistics.median(gaps),1) if gaps else 'not measured'} ms. Largest observed source gap among those encodings: {round(max(gaps),1) if gaps else 'not measured'} ms. Input stream FPS does not equal tracker throughput.

Deterministic mathematical tests cover irregular intervals and physical velocity, variable frame rates, repeated/backward/missing times, callback delay, dropped intervals, temporary single-hand loss, gaps between adjacent grid points, malformed input, and body-relative translation. These fixtures are not recordings or accuracy evidence.
""")
track=read(run/'v6-tracking-aggregate.json',[])
features=read(run/'v6-confusion-feature-aggregate.json',{})
text=['# Target-20 V6 browser/offline tracking parity','',
      'Same development source, approximately paired by the virtual three-second playback schedule and nearest native source timestamp. No frame-exact or same-decoded-pixel parity is claimed. Differences mix tracker build, resolution/padding, cadence, warm-up, and smoothing. Detection side disagreement is not proof of a swap.',
      '', '| Word | Browser / Python frames | Browser / Python median interval ms | Left longest runs B/P | Right longest runs B/P | Approx. pairs | Left/right presence disagreement | Raw body XY MAE |','|---|---:|---:|---:|---:|---:|---|---:|']
for r in track:
    b,o,a=r['browser'],r['offline'],r['aligned']
    fmt=lambda v:'—' if v is None else f'{v:.3f}'
    presence=lambda k:fmt(a[k]['presence_disagreement']) if a[k] else '—'
    text.append(f"| {r['word']} ({r['payload_run']}) | {b['frames']}/{o['frames']} | {b['median_delta_ms']:.1f}/{o['median_delta_ms']:.1f} | {b['hands']['left']['longest_run']}/{o['hands']['left']['longest_run']} | {b['hands']['right']['longest_run']}/{o['hands']['right']['longest_run']} | {r['aligned_pairs']} | {presence('left')}/{presence('right')} | {fmt(a['pose']['xy_mae'] if a['pose'] else None)} |")
text+=['','## Displacement and smoothing','']
for r in track:
    fmt=lambda d: ', '.join(f'{k}={v:.4f}' if v is not None else f'{k}=unobserved' for k,v in d.items())
    text.append(f"- **{r['word']}**: median step displacement browser [{fmt(r['browser']['median_step_xy'])}], Python smoothing on [{fmt(r['offline']['median_step_xy'])}], off [{fmt(r['offline_no_smoothing']['median_step_xy'])}]. Python initialization/first frame {r['offline_init_ms']:.1f}/{r['offline_first_frame_ms']:.1f} ms. Nearest-pair timestamp residual {r['alignment_nearest_median_ms']} ms (not sync error).")
controls=read(cache/'virtual-v6-controls'/'results.json',{}).get('results',[])
warmups=[(r.get('warmup') or {}).get('start_to_ready_ms') for r in controls]
text+=['',f'Browser start-to-ready (camera + tracker initialization and warm-up; controls run): {[round(x) for x in warmups if x is not None]} ms. This is not an isolated tracker initialization measurement.',
       'The private aggregate also records left/right raw XY displacement error on jointly visible pairs and per-side continuity transitions. Missing landmarks upstream are tracking/capture evidence, while an encoder rejection describes insufficient sequence support.']
write('tracking_parity','\n'.join(text))
text=['# Target-20 V6 confusion analysis','',
      'Development only. This checks source gloss metadata, tracking, crop boundaries and frozen V3 outputs. It is not a causal ablation and does not certify linguistic labels. V6 never produces a score or prediction.']
by_word={r['label']:r for r in rows}
prior={r['label']:r for r in read(cache/'virtual-v5-validation'/'results.json',{}).get('results',[]) if r['split']=='val'}
tr={r['word']:r for r in track}
for a,b in [('YES','YOU'),('GOOD','EAT'),('WHO','PLEASE')]:
    text+=['',f'## {a} versus {b}']
    for k in (a,b):
        r=by_word.get(k,{})
        d=r.get('backend_response') or {}
        q=tr.get(k,{})
        text.append(f"- {k}: source gloss {q.get('reference_gloss','not verified in paired payload')}; V3 top {d.get('rawTopLabel','not observed')}, score {d.get('topScore','not observed')}, accepted {r.get('predicted') or 'none'}. Legacy crop {q.get('legacy_crop_frames','unknown')}/{q.get('browser',{}).get('frames','unknown')} frames; largest legacy motion at visibility transition: {q.get('legacy_peak_at_visibility_transition','unknown')}.")
    historical=prior.get(a,{}).get('backend_response') or {}
    if historical:
        text.append(f"- V5 archival validation (not a V6 trial): {a} top {historical.get('rawTopLabel')}, score {historical.get('topScore')}, accepted {prior[a].get('predicted') or 'none'}.")
    text.append(f"- Single-clip V6 encoder comparison (may use tagged V5 payload for tracker dropout): {features.get(a+' / '+b,'insufficient paired observations')}. Descriptive only; overlap does not establish class equivalence.")
text+=['','No metadata mismatch is inferred merely from a wrong prediction. The listed legacy crop peaks and mask disagreement provide evidence of potential distortion, not proof that fixing them would change V3 output. Small class-level development counts limit claims about signer/variant diversity; model limitations and distribution shift remain plausible. No thresholds were changed.']
write('confusion_analysis','\n'.join(text))
tests=(cache/'target20-v6-tests.log').read_text(errors='replace')
test_summary='; '.join(re.findall(r'(?m)^(?:Ran .*|OK|FAILED.*)$',tests))
text=['# Target-20 V6 simulated virtual-camera report','',
      f"{len(rows)} distinct validation clips; {sum(bool(r.get('camera_configuration_ok')) for r in rows)} verified 640×480 / 15 FPS streams; {sum(bool(r.get('full_source_window_captured')) for r in rows)} full source windows; {len(responses)} API responses. Encoder states: {dict(encoder_states)}. V3 recognition states: {dict(v3)}. V3 end-to-end correct: {sum(bool(r.get('correct')) for r in rows)}/{len(rows)}. V6 recognition: not applicable.",
      '', 'Actual Chromium getUserMedia, HandSpeak frontend, browser Holistic and local Python API. V6 ran in parallel to V3 on the real capture request, not as input to V3. Capture failure is not model rejection. No exposed V4 clips were used for tuning or tested here.',
      '', '## Transformed validation controls']
for r in controls:
    d=r.get('backend_response') or {}
    text.append(f"- {r['scenario']}: {r.get('status') or r.get('error')}; V6 state {d.get('experimentalEncoder',{}).get('state','not submitted')}; accepted V3 prediction {r.get('predicted') or 'none'}. Not independent clips.")
compat=read(run/'v6-v3-compatibility.json',{})
text+=['',f"Exact legacy response parity: {compat.get('exact_response_matches','not verified')} real validation request replays matched every V3 response field, excluding only the V6 diagnostic field. Stable and locked model hashes were verified.",'',f'Automated suites: {test_summary or "pending"}.','',
       'Reproduction: start a loopback QA server on port 8001 with the locked V3 checkpoint and HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1; run training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output <new private directory>. The analysis scripts read the original private run folders. Raw recordings and submitted landmarks stay outside the served directory.']
write('virtual_camera_report','\n'.join(text))
print(len(rows),len(responses),encoder_states,len(track),test_summary)
