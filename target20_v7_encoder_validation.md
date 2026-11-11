# V7 validation of the independent V6 encoder

**Fixed:** The documented 200 ms gap bound was previously overridable up to 600 ms. The encoder now caps it at 200 ms, rejects timestamp-difference overflow even for finite endpoints, and bounds grid size before allocation. No V3 encoder change.

**Tests:** Independent masks, no motion from absent hands, visibility/gap boundaries, duplicate/backward timestamps, physical-time velocity, irregular cadence, callback delay, dropouts, minimum support and stable shoulder-relative coordinates. New tests include an oversized gap limit, overflow, and QA rejection/association contracts. Results: Ran 118 tests in 189.771s; OK; Ran 4 tests in 0.040s; OK.

**Observed:** V6 states {'encoded': 17, 'not_observed': 3}. Full frozen V3 response parity on 17 browser requests, excluding only the opt-in V6 diagnostic field. This is interface compatibility; V6 output was never passed into V3 and no V6 recognition result exists.
