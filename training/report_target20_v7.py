"""Generate aggregate V7 reports; never publish private video or landmarks."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,statistics
root=Path(__file__).resolve().parents[1]
cache=root.parent/'handspeak-training'
run=cache/'virtual-v7-validation'
def read(p,default=None):return json.loads(p.read_text()) if p.exists() else default
def write(name,s):(root/f'target20_v7_{name}.md').write_text(s.strip()+'\n',encoding='utf-8')
rows=read(run/'results.json',{}).get('results',[])
ctrl=read(cache/'virtual-v7-controls/results.json',{}).get('results',[])
blank=read(cache/'virtual-v7-blank-audit/results.json',{}).get('results',[])
assert all(r['split']=='val' for r in rows+ctrl)
assert len(rows)==len({r['source_sha256'] for r in rows})
cap=Counter(r['capture_outcome'] for r in rows)
enc=Counter(r['encoder_outcome'] for r in rows)
v3=Counter(r['v3_outcome'] for r in rows)
compat=read(run/'v6-v3-compatibility.json',{}).get('exact_response_matches','not yet verified')
tests=[]
final_log=(cache/'target20-v7-final-tests.log')
final_lines=re.findall(r'(?m)^(?:Ran .*|OK|FAILED.*)$',final_log.read_text(errors='replace')) if final_log.exists() else []
logs=['target20-v7-final-tests.log'] if len(final_lines)>=4 else ['target20-v7-tests.log','target20-v7-focused.log']
for log in logs:
    tests+=re.findall(r'(?m)^(?:Ran .*|OK|FAILED.*)$',(cache/log).read_text(errors='replace'))
tests='; '.join(tests)
mf=cache/'target20-v7-proposed-split.json'
m=read(mf)
counts=Counter(x['status'] for x in m['samples'])
by_word={r['label']:r for r in rows}
p=[]
for r in rows:
    for path in run.glob(f"playlist-*/parity-{r['case_id']}.json"):
        req=read(path)
        fs=req['frames'];t=[f['timestampMs'] for f in fs]
        d=r['backend_response'];e=d.get('experimentalEncoder',{})
        assert req['vocabulary']=='target20' and req['consent'] is True
        assert all(a<b for a,b in zip(t,t[1:])) and d['frames']==len(fs)
        if e.get('state')=='encoded':
            assert e['input_frames']==len(fs) and e['source_first_ms']==t[0] and e['source_last_ms']==t[-1]
        p.append((r['label'],len(fs),t[-1]-t[0],max(b-a for a,b in zip(t,t[1:])),req['capture']['durationMs'],
                  e.get('grid_last_ms',0)-e.get('grid_first_ms',0)))
warmups=[round(r['warmup']['start_to_ready_ms']) for r in rows if (r.get('warmup') or {}).get('start_to_ready_ms') is not None]
write('capture_reliability',f"""
# V7 capture reliability

The real browser opens the simulated stream, warms the tracker, counts down, serializes Holistic calls and posts captured landmarks. {len(rows)} distinct validation cases; {sum(bool(r.get('camera_configuration_ok')) for r in rows)} verified 640×480/15 FPS streams and {sum(bool(r.get('full_source_window_captured')) for r in rows)} full source windows. Outcomes: {dict(cap)}. Cold start to ready (camera plus tracker warm-up): {warmups} ms.

**QA fixes:** Bind responses to request objects issued by the current attempt, ignore stale responses, and fail ambiguous multiple requests. Distinguish capture, encoder and V3 states. Unknown rejection credit requires a verified normal capture and an actual model abstention; absent/failed requests and tracking failures earn no credit. Isolated non-playlist captures cannot earn unknown rejection credit without window verification. Require outputs outside the served tree.

**Payload checks:** {len(p)} real browser requests matched response frame counts. Timestamps increased strictly and V6 preserved source endpoints for encoded requests. Decode-frame totals include pre/post-roll and do not directly measure lost tracker frames.

| Word | Frames | Source span ms | Max gap ms | Capture duration ms | V6 active span ms |
|---|---:|---:|---:|---:|---:|
"""+'\n'.join(f'| {w} | {n} | {span:.1f} | {gap:.1f} | {dur:.1f} | {active:.1f} |' for w,n,span,gap,dur,active in p))
write('encoder_validation',f"""
# V7 validation of the independent V6 encoder

**Fixed:** The documented 200 ms gap bound was previously overridable up to 600 ms. The encoder now caps it at 200 ms, rejects timestamp-difference overflow even for finite endpoints, and bounds grid size before allocation. No V3 encoder change.

**Tests:** Independent masks, no motion from absent hands, visibility/gap boundaries, duplicate/backward timestamps, physical-time velocity, irregular cadence, callback delay, dropouts, minimum support and stable shoulder-relative coordinates. New tests include an oversized gap limit, overflow, and QA rejection/association contracts. Results: {tests}.

**Observed:** V6 states {dict(enc)}. Full frozen V3 response parity on {compat} browser requests, excluding only the opt-in V6 diagnostic field. This is interface compatibility; V6 output was never passed into V3 and no V6 recognition result exists.
""")
s=f'# V7 virtual camera — validation only\n\n{len(rows)} clips. Capture: {dict(cap)}. V6: {dict(enc)}. V3: {dict(v3)}.\n\n| Word | Capture | Encoder | V3 outcome | Accepted word | Top score |\n|---|---|---|---|---|---:|\n'
for word in m['labels']:
    r=by_word.get(word,{})
    d=r.get('backend_response') or {}
    s+=f"| {word} | {r.get('capture_outcome','not run')} | {r.get('encoder_outcome','not observed')} | {r.get('v3_outcome','not scored')} | {r.get('predicted') or '-'} | {d.get('topScore','-')} |\n"
s+='\nControls (not independent test clips):\n'
for r in ctrl:
    s+=f"- {r['scenario']}: {r.get('status') or r.get('error')}; {r['capture_outcome']}, {r['v3_outcome']}, rejection credit {r['unknown_rejected']}.\n"
s+='\nThe first timed no-hands control unexpectedly submitted landmarks. Its input pixels were not verified, so it cannot distinguish tracker hallucination from virtual stream/slot misalignment and is not a valid no-hands check. The follow-up samples only low-resolution pixel contrast during recording; no pixels are persisted.\n'
for r in blank:
    s+=f"- Blank-content audit: {r.get('blank_control_samples',0)} sampled frames; uniform input verified: {r.get('blank_control_verified','unobserved')}; {r['capture_outcome']}; V3 {r['v3_outcome']}. No rejection credit.\n"
s+='\nReproduce: local QA backend port 8001, frozen V3 and HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1. Run training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output <private directory>. Controls add --phase rejections --limit 8. No V4 test replay, physical camera, injected landmarks or accuracy claims.\n'
write('virtual_camera_report',s)
track=read(run/'v6-tracking-aggregate.json',[])
import mediapipe as mp
s=f"""
# V7 browser/Python tracking investigation

Browser Holistic 0.5.1675471629 versus Python MediaPipe {mp.__version__}, both complexity 1, 0.5 tracking/detection cutoffs and smoothing enabled for primary comparisons. Python smoothing off was also measured. Same public options do not guarantee the same tracker build or state.

Browser letterboxes to 640×480 and retimes to three seconds with idle padding; Python processes native frames at an approximate 15 FPS stride. Browser does a warm-up send before countdown, retains tracker state across captures, skips repeated/currently busy frames and uses a 65 ms processing guard. Python starts a fresh graph per clip. Measurements pair by approximate retimed timestamp, not identical decoded pixels. Raw XY is image-normalized; V6 subsequently uses shoulder centering and scale.

| Word | Source | Browser/Python median interval ms | Left longest run B/P | Right longest run B/P | Left/right presence disagreement | Body XY MAE |
|---|---|---|---|---|---|---:|
"""
for r in track:
    b,o,a=r['browser'],r['offline'],r['aligned']
    fmt=lambda x:'n/a' if x is None else f'{x:.3f}'
    s+=f"| {r['word']} | {r['payload_run']} | {b['median_delta_ms']:.1f}/{o['median_delta_ms']:.1f} | {b['hands']['left']['longest_run']}/{o['hands']['left']['longest_run']} | {b['hands']['right']['longest_run']}/{o['hands']['right']['longest_run']} | {fmt((a['left'] or {}).get('presence_disagreement'))}/{fmt((a['right'] or {}).get('presence_disagreement'))} | {fmt((a['pose'] or {}).get('xy_mae'))} |\n"
s+='\n### Smoothing and initialization\n'
for r in track:
    x,y=r['offline']['median_step_xy']['pose'],r['offline_no_smoothing']['median_step_xy']['pose']
    s+=f"- {r['word']}: Python graph initialization/first frame {r['offline_init_ms']:.1f}/{r['offline_first_frame_ms']:.1f} ms; median pose step smoothing on/off {x:.4f}/{y:.4f}. Approximate paired observations {r['aligned_pairs']}.\n"
s+='\nRun training/target20_v6_tracking.py virtual-v7-validation for private hand-coordinate, displacement and continuity aggregates. V5 fallback payloads, if available, are explicitly tagged and not counted as V7 captures. Presence disagreement is reproducible but not proof of hand swaps. Build, decoded pixels, padding, cadence and warm-up are confounded. No tracker setting or production frontend behavior was changed on this evidence.\n'
write('tracking_investigation',s)
cat=Counter(r['dataset'] for r in m['samples'] if r['status']=='unverified_catalog')
write('dataset_qualification',f"""
# V7 dataset qualification

Screened catalog entries: {dict(cat)}. None of these entries is a verified recording. No new media downloaded. Source identifiers and dataset-local signer IDs are private; unverified clip hashes remain null.

- [MS-ASL official project](https://www.microsoft.com/en-us/research/project/ms-asl/) and [Microsoft catalog](https://microsoft.github.io/data-for-society/dataset?d=MS-ASL-American-Sign-Language-Dataset): official metadata archive supplies source links, glosses and signer IDs. Linked footage availability, source-level rights, variants (including “thanks” as THANK YOU) and cross-corpus overlap are not verified.
- [WLASL author repository](https://github.com/dxli94/WLASL): clip/signer metadata screened. Missing-media archive requires the authors’ agreement. Release split signer IDs overlap (108 train/val, 104 train/test and 98 val/test measured in V6); new grouping, source rights and perceptual deduplication would be needed.
- [PopSign v2.1 data card](https://signdata.cc.gatech.edu/view/datasets/popsign_v2_1/index.html): CC BY 4.0 documented at release level; target variant availability, signer groups and overlap with prior HandSpeak usage remain unverified. Direct catalog transport did not validate in V6; no bypass or clip download.
- [ASL Citizen terms](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/): restricted existing research material. Local media hashes checked against the original manifest. No new linguistic or near-duplicate certification.

Admission requires accessible media, documented source reuse and redistribution status, gloss/variant review, source ID, exact and perceptual deduplication, and verifiable signer-group separation. Catalog counts do not establish any of these on their own.
""")
s=f"""
# V7 split readiness — frozen development proposal, no untouched test

Private manifest: ../handspeak-training/target20-v7-proposed-split.json. SHA-256: {hashlib.sha256(mf.read_bytes()).hexdigest()}. Counts: {dict(counts)}. Development eligibility is limited to existing restricted research with original source mappings and exact hash verification. Development unknowns are not independent acceptance cases. All official test entries already used by earlier work are excluded. External catalog entries are quarantined.

| Word | Dev train | Dev validation | Qualified untouched clips |
|---|---:|---:|---:|
"""
for w in m['labels']:
    c=Counter(x['status'] for x in m['samples'] if x['word']==w)
    s+=f"| {w} | {c['eligible_development_train']} | {c['eligible_development_val']} | 0 — blocked |\n"
s+='\nOfficial signer split intersections are empty for the ASL Citizen subset; held-out exact hashes were excluded from development. Cross-corpus signer and near-duplicate evidence remains incomplete. Reproduce with training/prepare_target20_v7_split.py; changes require a new frozen manifest before future evaluation.\n'
write('split_readiness',s)
write('final_status',f"""
# V7 final status — not ready for independent evaluation

QA request association and outcome reporting repaired; V6 gap and timestamp guards hardened. Production frontend, V3 model, inference, threshold, default and checkpoints not changed. Exact V3 response replays: {compat}. Stable and locked hashes are checked by the replay script. No training or promotion.

Validation-only simulated browser run: {len(rows)} clips. Capture {dict(cap)}. Encoder {dict(enc)}. V3 {dict(v3)}. Suites: {tests}. Passing software tests are not recognition accuracy.

Data: {dict(counts)}; zero qualified untouched test clips. No independent all-20 signer-separated dataset is ready. The blockers are source media authorization and availability, variants, and independent signer/hash/perceptual duplicate checks, not camera hardware.

Changed code: target20_encoder_v6.py, training/target20_virtual_camera.py, training/target20_v6_tracking.py, training/check_target20_v6_compatibility.py, training/test_target20_v7.py, training/prepare_target20_v7_split.py, training/report_target20_v7.py. Seven V7 reports and the private manifest are new. Prior reports and checkpoints remain intact.
""")
print(len(rows),dict(cap),dict(enc),dict(v3),len(p),tests)
