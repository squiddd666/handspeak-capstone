# V5 dataset audit

No new dataset is admitted for training or untouched evaluation. The private V5 development manifest contains only existing ASL Citizen train/validation records. Its signer and hash identifiers do not overlap with the existing test split. The official test has already been exposed and is excluded.

| Target | Development train | Development validation | Newly qualified untouched test |
|---|---:|---:|---:|
| HELLO | 14 | 4 | 0 |
| THANK YOU | 16 | 3 | 0 |
| PLEASE | 14 | 4 | 0 |
| SORRY | 15 | 3 | 0 |
| YES | 15 | 5 | 0 |
| NO | 16 | 3 | 0 |
| HELP | 13 | 5 | 0 |
| LOVE | 13 | 5 | 0 |
| I / ME | 13 | 5 | 0 |
| YOU | 15 | 4 | 0 |
| WANT | 31 | 7 | 0 |
| NEED | 15 | 3 | 0 |
| LIKE | 15 | 3 | 0 |
| GOOD | 15 | 4 | 0 |
| BAD | 13 | 4 | 0 |
| WHAT | 31 | 7 | 0 |
| WHERE | 14 | 4 | 0 |
| WHO | 14 | 4 | 0 |
| EAT | 30 | 7 | 0 |
| WATER | 14 | 4 | 0 |

All 20 labels are represented for development; all 20 are missing from a newly qualified untouched benchmark.

- [ASL Citizen official splits](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-description/) and [research license](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/): already used. No redistribution of raw or derived data.
- [MS-ASL official catalog](https://microsoft.github.io/data-for-society/dataset?d=MS-ASL-American-Sign-Language-Dataset): candidate catalog with signer IDs and video references. Full target coverage, source media access/permission and cross-dataset signer/recording deduplication are not verified.
- [WLASL authors’ paper](https://arxiv.org/abs/1910.11006): word-level candidate; per-clip rights, source availability and cross-dataset overlap not cleared here.
- [PopSign authors’ supplement](https://signdata.cc.gatech.edu/res/doc/popsign_v1_0/popsign_v1_0_supplemental.pdf): candidate for a coverage audit; some material is already used elsewhere in HandSpeak and cannot automatically be declared untouched.

External blocker: a verified, authorized, signer-separated set covering all 20 words plus independently selected unknown signs. Catalog hits alone are not eligible samples.

## MS-ASL metadata coverage (not admitted)

| Target | Exact catalog label | Train | Validation | Test |
|---|---|---:|---:|---:|
| HELLO | hello | 30 | 14 | 20 |
| THANK YOU | Missing | 0 | 0 | 0 |
| PLEASE | please | 39 | 10 | 8 |
| SORRY | sorry | 25 | 19 | 5 |
| YES | yes | 46 | 16 | 3 |
| NO | no | 46 | 18 | 9 |
| HELP | help | 40 | 11 | 5 |
| LOVE | love | 22 | 13 | 4 |
| I / ME | me, i | 45 | 11 | 5 |
| YOU | you | 35 | 13 | 4 |
| WANT | want | 53 | 8 | 8 |
| NEED | need | 38 | 11 | 13 |
| LIKE | like | 48 | 17 | 6 |
| GOOD | good | 37 | 18 | 10 |
| BAD | bad | 27 | 14 | 8 |
| WHAT | what | 48 | 12 | 6 |
| WHERE | where | 46 | 9 | 5 |
| WHO | who | 33 | 11 | 7 |
| EAT | eat | 57 | 11 | 9 |
| WATER | water | 41 | 9 | 6 |

Official metadata signer-ID overlaps: train/validation 0, train/test 0, validation/test 0. An ID is dataset-local; no cross-corpus identity mapping was assumed.

No video was downloaded from this catalog. Counts are candidate annotations, not verified accessible or authorized recordings. Aliases need linguistic review.

MS-ASL lists **thanks** as a possible THANK YOU alias, but not the exact label. The alias was not admitted without linguistic verification.
