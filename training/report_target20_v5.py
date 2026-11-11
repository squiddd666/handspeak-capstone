"""Publish V5 aggregate validation-only browser diagnostics."""
from pathlib import Path
import csv,json,re,statistics
root=Path(__file__).resolve().parents[1]
cache=root.parent/'handspeak-training'
run=cache/'virtual-v5-validation'
read=lambda name:json.loads((run/name).read_text(encoding='utf-8'))
rows=read('results.json')['results'] if (run/'results.json').exists() else [json.loads(l) for f in run.glob('playlist-*/results.jsonl') for l in f.read_text().splitlines()]
labels=json.loads((root/'target20_evaluation.json').read_text())['labels'][:20]
by_word={r['label']:r for r in rows}
assert len(by_word)==len(rows) and all(r['split']=='val' for r in rows)
out=[]
for word in labels:
    r=by_word.get(word,{})
    d=r.get('backend_response') or {}
    diag=(r.get('capture_diagnostics') or [{}])[-1]
    out.append(dict(word=word,split='validation',attempt_logged=bool(r),verified_640x480_15fps=bool(r.get('camera_configuration_ok')),
                    full_source_window=bool(r.get('full_source_window_captured')),decoded_frames=r.get('delivered_frames_during_attempt'),visible_hand_frames=diag.get('handFrames'),
                    api_status=r.get('http_status'),backend_state=d.get('state'),score=d.get('topScore'),gate=d.get('minScore'),prediction=r.get('predicted'),
                    displayed=r.get('display') if r.get('predicted') else None,correct=bool(r.get('correct')),status=r.get('status') or r.get('error')))
with (root/'target20_v5_per_word_results.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
p=read('parity-aggregate.json') if (run/'parity-aggregate.json').exists() else []
lines=['# V5 browser/offline parity — validation only','',
       'Browser payloads were passively retained from real frontend POSTs in the private research cache. No landmark payload was injected. Offline tensor comparisons use the corresponding cached clip; matching the source clip does not imply identical decoded timestamps or tracker state.',
       '',f'{len(p)} browser/cached pairs; {sum(r["api_score_verified"] for r in p)} exact top-label / score checks (tolerance 0.00002). Input shape 4 × 32 × 27; the two hand masks are separate. Coordinates are shoulder-centered XY; velocities are per resampled frame, not per physical second.',
       '', '| Word | Browser frames | Median source interval ms | Body normalized XY MAE | Left / right mask disagreement | Velocity MAE | Mean score difference |',
       '|---|---:|---:|---:|---:|---:|---:|']
for r in p:
    lines.append(f'| {r["word"]} | {r["browser_frames"]} | {r["browser_median_interval_ms"]:.1f} | {r["body_xy_mae"]:.4f} | {r["left_mask_disagreement"]:.1%} / {r["right_mask_disagreement"]:.1%} | {r["velocity_mae"]:.4f} | {r["score_mae"]:.4f} |')
lines+=['','Approximate raw XY timestamp matches (source time scaled to the three-second virtual clip; not exact decoded-frame pairing):']
for r in p:
    if 'raw_approximate_time_pairs' in r:
        lines.append(f'- {r["word"]}: {r["raw_approximate_time_pairs"]} pairs; body/left/right XY MAE {r.get("pose_raw_xy_mae")} / {r.get("left_raw_xy_mae")} / {r.get("right_raw_xy_mae")}. Missing-side agreement is recorded in the private aggregate; no hand swap is inferred from missing detections alone.')
lines+=['','Shared tensor preprocessing and score replay are verified for matched inputs; **raw extraction equivalence is not established**. Normalized, jointly-visible per-hand XY errors and side-presence disagreements are retained in the private aggregate. Browser WASM and Python Holistic differ in build, input cadence, decoded pixels, idle padding and smoothing history. The legacy crop and interpolation remain frozen for v3.']
(root/'target20_v5_pipeline_parity.md').write_text('\n'.join(lines),encoding='utf-8')
started=sum(r['verified_640x480_15fps'] for r in out)
full=sum(r['full_source_window'] for r in out)
api=sum(r['api_status']==200 for r in out)
ok=sum(r['correct'] for r in out)
(root/'target20_v5_virtual_camera_report.md').write_text(f"""# V5 simulated virtual-camera diagnostic

{len(rows)}/20 validation cases logged, one distinct source clip per available label. {started} verified streams, {full} verified full source windows, {api} HTTP 200 responses and {ok} correct end-to-end predictions. This is a development run, not an independent benchmark. V4 test clips were not replayed or used for tuning.

Chromium file-backed getUserMedia delivered 640×480 at 15 FPS via the actual HandSpeak UI, browser Holistic and the local Python service. Tracker throughput can be lower than input FPS. Capture time and quality failures are distinct from model confidence. Backend scores are uncalibrated. See the per-word CSV for frontend output, capture diagnostics and backend status.

Reproduce with a local QA server on port 8001 using the private frozen v3 checkpoint, then run training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output <new private directory>. The V5 parity and report scripts read the original private run folder virtual-v5-validation. No physical webcam is required.
""",encoding='utf-8')
controls=cache/'virtual-v5-controls'/'results.json'
if controls.exists():
    report_path=root/'target20_v5_virtual_camera_report.md'
    with report_path.open('a',encoding='utf-8') as f:
        f.write('\n## Invalid-input controls (validation transformations)\n\n')
        for r in json.loads(controls.read_text())['results']:
            f.write(f"- {r['scenario']}: {r.get('status') or r.get('error')}; backend response {'present' if r.get('backend_response') else 'absent'}. No capture failure is credited as model rejection.\n")
tests=(cache/'target20-v5-tests.log').read_text(errors='replace')
status='; '.join(re.findall(r'(?m)^(?:Ran .*|OK|FAILED.*)$',tests)) or 'not completed'
(root/'target20_v5_acceptance_checklist.md').write_text(f"""# V5 acceptance checklist — not accepted

- Complete: 200 V4 cases audited with primary and overlapping evidence.
- Complete: capture preflight, consent recheck and source-time instrumentation; same-input encoding/score parity verified where observed.
- Software suites: {status}.
- Diagnostic only: {len(rows)}/20 development browser clips; {ok} correct. Not 10 untouched clips per word.
- Not established: frame-exact raw tracker parity, untouched test macro F1, independent per-word recall and browser unknown-sign rejection.
- Not met: 90% validation macro F1 on the frozen candidate.
- Blocked for a scientifically valid next candidate: no qualified independent all-20 dataset. No retraining, threshold changes, checkpoint overwrite or promotion.
- Physical camera: out of scope.
""",encoding='utf-8')
print(len(rows),started,full,api,ok,len(p),status)
