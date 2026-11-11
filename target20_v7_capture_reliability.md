# V7 capture reliability

The real browser opens the simulated stream, warms the tracker, counts down, serializes Holistic calls and posts captured landmarks. 20 distinct validation cases; 20 verified 640×480/15 FPS streams and 18 full source windows. Outcomes: {'verified': 16, 'capture_failure': 1, 'insufficient_tracking': 3}. Cold start to ready (camera plus tracker warm-up): [62309] ms.

**QA fixes:** Bind responses to request objects issued by the current attempt, ignore stale responses, and fail ambiguous multiple requests. Distinguish capture, encoder and V3 states. Unknown rejection credit requires a verified normal capture and an actual model abstention; absent/failed requests and tracking failures earn no credit. Isolated non-playlist captures cannot earn unknown rejection credit without window verification. Require outputs outside the served tree.

**Payload checks:** 17 real browser requests matched response frame counts. Timestamps increased strictly and V6 preserved source endpoints for encoded requests. Decode-frame totals include pre/post-roll and do not directly measure lost tracker frames.

| Word | Frames | Source span ms | Max gap ms | Capture duration ms | V6 active span ms |
|---|---:|---:|---:|---:|---:|
| HELLO | 40 | 3974.4 | 137.2 | 4069.1 | 848.1 |
| THANK YOU | 38 | 3968.4 | 142.2 | 4080.4 | 1347.1 |
| PLEASE | 36 | 3956.6 | 132.9 | 4062.2 | 1181.2 |
| SORRY | 36 | 3964.4 | 137.2 | 4063.3 | 1017.2 |
| YES | 36 | 3976.4 | 140.4 | 4086.9 | 1188.7 |
| NO | 34 | 3925.3 | 144.2 | 4041.8 | 1007.1 |
| HELP | 40 | 3955.0 | 129.0 | 4043.3 | 941.4 |
| LOVE | 44 | 3996.7 | 154.9 | 4102.8 | 1059.3 |
| I / ME | 36 | 3881.8 | 142.0 | 4013.5 | 900.0 |
| YOU | 41 | 3990.3 | 138.3 | 4085.8 | 967.8 |
| WANT | 33 | 3994.5 | 158.0 | 4126.4 | 1328.2 |
| NEED | 27 | 3943.3 | 198.3 | 4074.6 | 1875.7 |
| GOOD | 42 | 3948.9 | 115.4 | 4044.4 | 881.8 |
| BAD | 35 | 3998.5 | 178.2 | 4101.5 | 1288.9 |
| WHAT | 40 | 3936.8 | 142.2 | 4077.1 | 831.0 |
| WHERE | 39 | 3909.7 | 144.7 | 4045.6 | 904.7 |
| EAT | 34 | 3939.3 | 174.2 | 4037.7 | 972.3 |
