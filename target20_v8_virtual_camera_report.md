# V8 virtual-camera verification (simulated)

The actual HandSpeak UI used Chromium file-backed getUserMedia and the real QA Python backend. No physical camera, landmark injection or exposed test material. One ASL Citizen development validation source per target; no independent accuracy inference.

- 20 scheduled and all 20 camera configurations verified (640×480, 15 FPS source).
- 16/20 full source-window checks passed. A full window does not guarantee tracking.
- 12/20 archived browser submissions, all V6 encoded with original browser timestamps. 10 verified captures were usable; HELP and NEED encoded but missed the source window and were excluded.
- Eight tracking/continuity failures did not submit. No rejection or accuracy credit for capture failures.
- Of 10 verified cases, V3 abstained nine times and recognized YES incorrectly as YOU once. Zero correct. The raw score is uncalibrated and not necessarily a displayed prediction.
- Repeat of the first three same-source development clips: 3 verified cameras, 2 full windows, 1 usable capture, and 1 wrong V3 recognition (HELLO as PLEASE). Not independent attempts.
- Exact V3 response equality with diagnostics absent on all 13 archived requests across both runs; the opt-in V6 diagnostic field was removed for comparison. Both checkpoint hashes verified. No V6 encoding was fed into V3.
- Malformed and insufficient sequence behavior was exercised by automated tests; the eight real insufficient-tracking cases also verify non-submission. No new independent unknown set was scored.

| Label | Full window | Capture | V6 | V3 | Raw top / score |
|---|---|---|---|---|---|
| HELLO | yes | verified | encoded | abstention | NO / .726647 |
| THANK YOU | yes | verified | encoded | abstention | HELP / .816293 |
| PLEASE | yes | verified | encoded | abstention | HELP / .276745 |
| SORRY | yes | verified | encoded | abstention | I / ME / .708992 |
| YES | yes | verified | encoded | incorrect | YOU / .989895 |
| NO | yes | insufficient tracking | no submission | not scored | — |
| HELP | no | window failed | encoded, excluded | not scored | YES / .563037 |
| LOVE | no | insufficient tracking | no submission | not scored | — |
| I / ME | no | insufficient tracking | no submission | not scored | — |
| YOU | yes | verified | encoded | abstention | BAD / .628886 |
| WANT | yes | verified | encoded | abstention | WHAT / .856273 |
| NEED | no | window failed | encoded, excluded | not scored | WHERE / .887340 |
| LIKE | yes | insufficient tracking | no submission | not scored | — |
| GOOD | yes | insufficient tracking | no submission | not scored | — |
| BAD | yes | verified | encoded | abstention | WATER / .965038 |
| WHAT | yes | insufficient tracking | no submission | not scored | — |
| WHERE | yes | verified | encoded | abstention | GOOD / .972555 |
| WHO | yes | insufficient tracking | no submission | not scored | — |
| EAT | yes | verified | encoded | abstention | SORRY / .613381 |
| WATER | yes | insufficient tracking | no submission | not scored | — |

Evidence: private results.json, protocol.json, canonical-v1/index.json and v6-v3-compatibility.json for each run; reproduce using target20_v8_canonical_extraction.md.
