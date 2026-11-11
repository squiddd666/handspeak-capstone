# Target-20 physical webcam report — BLOCKED

The user explicitly confirmed that no physical webcam or ASL signer is available. Windows Camera/Image enumeration returned no present devices. No physical recording was counted. Prerecorded reference videos are not substituted for real-user attempts.

| Word | Required independent attempts | Actual attempts | Correct | Status |
| --- | ---: | ---: | ---: | --- |
| HELLO | 10 | 0 | Not measured | BLOCKED |
| THANK YOU | 10 | 0 | Not measured | BLOCKED |
| PLEASE | 10 | 0 | Not measured | BLOCKED |
| SORRY | 10 | 0 | Not measured | BLOCKED |
| YES | 10 | 0 | Not measured | BLOCKED |
| NO | 10 | 0 | Not measured | BLOCKED |
| HELP | 10 | 0 | Not measured | BLOCKED |
| LOVE | 10 | 0 | Not measured | BLOCKED |
| I / ME | 10 | 0 | Not measured | BLOCKED |
| YOU | 10 | 0 | Not measured | BLOCKED |
| WANT | 10 | 0 | Not measured | BLOCKED |
| NEED | 10 | 0 | Not measured | BLOCKED |
| LIKE | 10 | 0 | Not measured | BLOCKED |
| GOOD | 10 | 0 | Not measured | BLOCKED |
| BAD | 10 | 0 | Not measured | BLOCKED |
| WHAT | 10 | 0 | Not measured | BLOCKED |
| WHERE | 10 | 0 | Not measured | BLOCKED |
| WHO | 10 | 0 | Not measured | BLOCKED |
| EAT | 10 | 0 | Not measured | BLOCKED |
| WATER | 10 | 0 | Not measured | BLOCKED |

Speed, distance, lighting, background, position, incomplete/unknown signs, temporary tracking loss, and end-to-end latency remain unmeasured on a real webcam.
Automated capture-controller tests and direct/API recorded-landmark tests are software checks only, not independent webcam attempts.

Resume with a connected webcam and a consenting ASL signer. Use the real browser panel, explicitly enable server landmark processing, perform 10 fresh complete attempts per word, and record expected label, predicted label/state, latency, condition, tracking failures and attempt identifier. Preserve all failures. Reserve new signers/data before tuning again.

## Browser-only observations

The actual HandSpeak interface displayed all 20 words. Selecting practice did not check server consent; Record was refused with “Enable landmark processing for this model first.” A camera startup attempt timed out with no video track. No physical signing, no simulated reference video, and no completed webcam recording were counted. See target20_browser_consent_check.png for the consent observation.
