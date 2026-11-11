# V8 QA state audit

The V7 NEED case legitimately reached the local backend. Its one associated
browser request contained 27 frames, 13 with a hand observed; the server
returned HTTP 200 and V6 encoded it. The browser source timestamps span
194213.544–198156.872 ms. The capture diagnostic says recording began at
194.209207 s and ended at 198.283642 s. The slot began at 192 s, so the QA
start cutoff was 194.100 s. Capture started about 109 ms late. The frontend
does not know a QA source slot's expected window, and an internally valid
sequence does not prove it covered that slot. Therefore V6 encoded, but
capture qualification failed and V3 was not scored. The V3 response was
uncertain (raw top WHERE at 0.889164); it was not a credited rejection.

| Run | Scheduled distinct clips | Verified device settings | Full-window flags | Archived requests/HTTP responses | V6 encoded | QA-qualified captures |
|---|---:|---:|---:|---:|---:|---:|
| V7 validation | 20 | 20 | 18 | 17 | 17 | 16 |
| V6 validation | 20 | 20 | 20 | 19 | 19 | Not measured with the V7 contract |

V7's 18 full-window flags include two cases with inadequate tracking that did
not submit. Three cases did not submit in all: LIKE, WHO and WATER. NEED
submitted but missed the QA window. Thus 16 qualified cases = 17 submissions
minus NEED. The 19 count is V6's validation batch, not V7's; warm-up and
transformed controls are separate. “Archived requests” means matched saved
payloads and corresponding responses, not all network activity or retries.

Evidence: private virtual-v7-validation/results.json and parity-11.json;
compare private virtual-v6-validation/results.json and its archived payload
count. No scoring rule needed changing. A V8 regression test recreates the
NEED lifecycle with a nominal unknown label and verifies that neither
verified-capture nor unknown-rejection credit is granted.
