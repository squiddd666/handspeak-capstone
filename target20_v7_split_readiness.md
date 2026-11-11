# V7 split readiness — frozen development proposal, no untouched test

Private manifest: ../handspeak-training/target20-v7-proposed-split.json. SHA-256: ad9e1df162fe2afe5d153d97e87c006be1076c44b6d4592d7ebcf8e885e45663. Counts: {'eligible_development_train': 336, 'unknown_candidate': 309, 'eligible_development_val': 88, 'excluded': 510, 'unverified_catalog': 1547}. Development eligibility is limited to existing restricted research with original source mappings and exact hash verification. Development unknowns are not independent acceptance cases. All official test entries already used by earlier work are excluded. External catalog entries are quarantined.

| Word | Dev train | Dev validation | Qualified untouched clips |
|---|---:|---:|---:|
| HELLO | 14 | 4 | 0 — blocked |
| THANK YOU | 16 | 3 | 0 — blocked |
| PLEASE | 14 | 4 | 0 — blocked |
| SORRY | 15 | 3 | 0 — blocked |
| YES | 15 | 5 | 0 — blocked |
| NO | 16 | 3 | 0 — blocked |
| HELP | 13 | 5 | 0 — blocked |
| LOVE | 13 | 5 | 0 — blocked |
| I / ME | 13 | 5 | 0 — blocked |
| YOU | 15 | 4 | 0 — blocked |
| WANT | 31 | 7 | 0 — blocked |
| NEED | 15 | 3 | 0 — blocked |
| LIKE | 15 | 3 | 0 — blocked |
| GOOD | 15 | 4 | 0 — blocked |
| BAD | 13 | 4 | 0 — blocked |
| WHAT | 31 | 7 | 0 — blocked |
| WHERE | 14 | 4 | 0 — blocked |
| WHO | 14 | 4 | 0 — blocked |
| EAT | 30 | 7 | 0 — blocked |
| WATER | 14 | 4 | 0 — blocked |

Official signer split intersections are empty for the ASL Citizen subset; held-out exact hashes were excluded from development. Cross-corpus signer and near-duplicate evidence remains incomplete. Reproduce with training/prepare_target20_v7_split.py; changes require a new frozen manifest before future evaluation.
