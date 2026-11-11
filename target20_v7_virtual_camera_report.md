# V7 virtual camera — validation only

20 clips. Capture: {'verified': 16, 'capture_failure': 1, 'insufficient_tracking': 3}. V6: {'encoded': 17, 'not_observed': 3}. V3: {'abstention': 15, 'incorrect': 1, 'not_scored': 4}.

| Word | Capture | Encoder | V3 outcome | Accepted word | Top score |
|---|---|---|---|---|---:|
| HELLO | verified | encoded | abstention | - | 0.821475 |
| THANK YOU | verified | encoded | abstention | - | 0.961787 |
| PLEASE | verified | encoded | abstention | - | 0.430758 |
| SORRY | verified | encoded | abstention | - | 0.41523 |
| YES | verified | encoded | incorrect | YOU | 0.995341 |
| NO | verified | encoded | abstention | - | 0.354803 |
| HELP | verified | encoded | abstention | - | 0.354193 |
| LOVE | verified | encoded | abstention | - | 0.423325 |
| I / ME | verified | encoded | abstention | - | 0.690961 |
| YOU | verified | encoded | abstention | - | 0.655595 |
| WANT | verified | encoded | abstention | - | 0.895517 |
| NEED | capture_failure | encoded | not_scored | - | 0.889164 |
| LIKE | insufficient_tracking | not_observed | not_scored | - | - |
| GOOD | verified | encoded | abstention | - | 0.971183 |
| BAD | verified | encoded | abstention | - | 0.968431 |
| WHAT | verified | encoded | abstention | - | 0.900225 |
| WHERE | verified | encoded | abstention | - | 0.889118 |
| WHO | insufficient_tracking | not_observed | not_scored | - | - |
| EAT | verified | encoded | abstention | - | 0.777566 |
| WATER | insufficient_tracking | not_observed | not_scored | - | - |

Controls (not independent test clips):
- no-hands: Unknown sign — no word added.; verified, abstention, rejection credit False.
- incomplete: No confident match. Sign again.; verified, abstention, rejection credit False.
- missing-hands: Unknown sign — no word added.; verified, abstention, rejection credit False.
- low-quality: Recording timed out before a complete capture. Nothing was submitted.; capture_failure, not_scored, rejection credit False.
- delayed: Capture quality insufficient: hand visibility or frame continuity. Nothing was submitted.; insufficient_tracking, not_scored, rejection credit False.
- dropped-frames: Unknown sign — no word added.; verified, abstention, rejection credit False.
- interrupted: Beginner recording canceled.; capture_failure, not_scored, rejection credit False.
- normal: Capture quality insufficient: hand visibility or frame continuity. Nothing was submitted.; insufficient_tracking, not_scored, rejection credit False.

The first timed no-hands control unexpectedly submitted landmarks. Its input pixels were not verified, so it cannot distinguish tracker hallucination from virtual stream/slot misalignment and is not a valid no-hands check. The follow-up samples only low-resolution pixel contrast during recording; no pixels are persisted.
- Blank-content audit: 33 sampled frames; uniform input verified: True; capture_failure; V3 not_scored. No rejection credit.

Reproduce: local QA backend port 8001, frozen V3 and HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1. Run training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output <private directory>. Controls add --phase rejections --limit 8. No V4 test replay, physical camera, injected landmarks or accuracy claims.
