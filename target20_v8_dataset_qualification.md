# V8 dataset qualification

No new media was admitted or downloaded. The frozen V7 inventory retains 1,193 MS-ASL and 354 WLASL catalog rows as **unverified**, not independent recordings.

| Source | Verified evidence | Admission blocker |
|---|---|---|
| [MS-ASL official project](https://www.microsoft.com/en-us/research/project/ms-asl/) | Publisher catalog includes glosses, source links and dataset-local signer IDs. | Actual footage access, applicable source permissions, alias/variant review, and cross-corpus signer and duplicate checks are unresolved. |
| [WLASL author repository](https://github.com/dxli94/WLASL) | Catalog has clip and signer metadata; author agreement applies to the missing-media archive. | Source access and permissions are unverified; published splits are not signer-disjoint (V6 found 108 train/val, 104 train/test and 98 val/test shared signer IDs). Re-grouping and cross-corpus checks are required. |
| [PopSign v2.1 data card](https://signdata.cc.gatech.edu/view/datasets/popsign_v2_1/index.html) | CC BY 4.0 is stated for the release. | Earlier direct catalog retrieval failed TLS validation. Actual target media access, variants, signer groups and prior HandSpeak overlap have not been verified. |
| [ASL Citizen license](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/) | Existing private research subset with local hashes and participant IDs; V8 used development validation only. | No new, demonstrably untouched holdout was qualified. No footage or landmark redistribution. |

Per-recording gloss/variant and duplicate status remains unverified for external catalog rows. Admission requires accessible authorized media, human gloss and variant review, identity/group provenance, exact and perceptual deduplication against development and exposed sources, and defensible signer separation. A dataset-local signer ID alone does not prove cross-corpus separation.
