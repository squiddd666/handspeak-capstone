# Target-20 V6 data readiness

No new videos admitted. Counts below are **catalog evidence**, not verified footage, independent evaluation material, or permission to use individual clips. PopSign per-word availability is unverified; the official project page documents the dataset-level license but the direct catalog TLS chain could not be verified in this environment. No certificate bypass was used.

| Target | Existing dev train / val | MS-ASL catalog | WLASL catalog clips | PopSign verified coverage | New eligible untouched |
|---|---:|---|---:|---|---:|
| HELLO | 14 / 4 | hello | 13 | Unverified | 0 |
| THANK YOU | 16 / 3 | thanks (alias unverified) | 14 | Unverified | 0 |
| PLEASE | 14 / 4 | please | 15 | Unverified | 0 |
| SORRY | 15 / 3 | sorry | 14 | Unverified | 0 |
| YES | 15 / 5 | yes | 22 | Unverified | 0 |
| NO | 16 / 3 | no | 22 | Unverified | 0 |
| HELP | 13 / 5 | help | 22 | Unverified | 0 |
| LOVE | 13 / 5 | love | 12 | Unverified | 0 |
| I / ME | 13 / 5 | me, i | 16 | Unverified | 0 |
| YOU | 15 / 4 | you | 16 | Unverified | 0 |
| WANT | 31 / 7 | want | 19 | Unverified | 0 |
| NEED | 15 / 3 | need | 18 | Unverified | 0 |
| LIKE | 15 / 3 | like | 21 | Unverified | 0 |
| GOOD | 15 / 4 | good | 16 | Unverified | 0 |
| BAD | 13 / 4 | bad | 16 | Unverified | 0 |
| WHAT | 31 / 7 | what | 21 | Unverified | 0 |
| WHERE | 14 / 4 | where | 15 | Unverified | 0 |
| WHO | 14 / 4 | who | 25 | Unverified | 0 |
| EAT | 30 / 7 | eat | 19 | Unverified | 0 |
| WATER | 14 / 4 | water | 18 | Unverified | 0 |

WLASL release metadata signer-ID intersections (entire catalog): train/val 108, train/test 104, val/test 98. These IDs do not prove disjointness across corpora. No clips were retrieved; original source permissions, duplicate videos and cross-corpus signer identity still need verification.

- [MS-ASL official metadata catalog](https://microsoft.github.io/data-for-society/dataset?d=MS-ASL-American-Sign-Language-Dataset): V5 catalog checks found no within-release signer-ID overlaps; aliases, rights, access and overlaps with other corpora remain unverified.
- [WLASL author repository](https://github.com/dxli94/WLASL): published v0.3 catalog inspected; release terms do not establish rights to every underlying web video.
- [PopSign v2.1 official data card](https://signdata.cc.gatech.edu/view/datasets/popsign_v2_1/index.html): CC BY 4.0 at dataset level; verify exact variants, available footage, split signers and reuse before admission.
- [ASL Citizen research terms](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/): existing development material only; exposed V4 known clips excluded from V6 diagnostics.

Blocker: no all-20 untouched, authorized signer-separated benchmark has been qualified. To admit material, verify source-level rights and usable clips, have aliases/variants reviewed, deduplicate clip hashes and near-duplicates, resolve signer groups across sources and freeze split assignments before evaluating. Do not redistribute research clips or raw landmarks.
