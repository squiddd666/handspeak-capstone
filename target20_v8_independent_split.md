# V8 independent split status

**Blocked: zero qualified untouched known clips for each of the 20 target glosses.** No new split was frozen. Preserve private V7 proposed manifest SHA-256 `ad9e1df162fe2afe5d153d97e87c006be1076c44b6d4592d7ebcf8e885e45663`.

| Partition | Existing rows | Status |
|---|---:|---|
| Development train | 336 | Existing only; no training in V8 |
| Development validation | 88 | Only partition used for V8 browser capture |
| Untouched known test | 0 | All 20 glosses lack qualified independent examples |
| Development unknown candidates | 309 | Not an untouched unknown benchmark |
| Exposed official test | 510 | Excluded |
| Unverified external catalog entries | 1,547 | Quarantined |

Before future evaluation, qualify media and signer groups, screen exact/perceptual overlap across all partitions and exposed sources, establish known and unknown evaluation sets, and freeze manifest plus SHA-256 before scoring. V8 repeat playbacks are never independent attempts.

Verify the retained manifest with `Get-FileHash ../handspeak-training/target20-v7-proposed-split.json -Algorithm SHA256`.
