# Sign avatar assets

## Active model

- **`signer.glb`** — [Kai](https://vtubeme.com/free-vrm-avatars/kai) (VTubeMe), cartoon young adult (short dark hair, graphic tee).
- Format: GLB (~9.34 MB), with embedded textures.
- License: **CC BY 4.0** — free for educational/commercial use; credit [VTubeMe](https://vtubeme.com) with a link back.
- Skeleton verified in this repo: **40 finger bones** (`Left/RightHand` + Thumb/Index/Middle/Ring/Pinky 1–4), independent wrists, full body.
- Face: **66 unique morph targets** including `eyeBlinkLeft/Right`, brow, mouth smile, and ARKit-style shapes.

## Motion sources (Watch & Practice priority)

0. **`reference/*-reference.glb`** — the 40 currently displayed local reference
   performances reconstructed with separate anatomical hands, per-segment
   fingers/palms and a shared video clock. Used only for the matching source
   video; depth/occluded fingers remain estimated. See [`reference/README.md`](reference/README.md).

1. **`clips/*-studio-galt.glb`** — Kai-retargeted ASL motion capture for HELLO, PLEASE, BYE, MY, BROTHER and BUY, including all finger joints. Retained when there is no matching reference reconstruction. The four new words are 3D learning examples, not new camera models. See [`clips/README.md`](./clips/README.md).
2. **`clips/*-kai-authored.glb`** — Kai-native hand-authored approximations for FISH, PAIN, SEE, SICK and NIGHT. Distinct sign paths, anatomical finger shapes and safe rest poses; not new captured mocap. Their existing reference videos and experimental camera previews are preserved.
3. **`sign-animations.js`** — Hand-authored fallback for other gestures or unavailable mocap. Together these sources cover all 47 currently listed Watch & practice words.
4. Optional `baked/` and `hand_cleanup/` exports can supplement legacy clips when installed; they are not currently bundled.

## Candidate comparison (finger bones inspected from GLB JSON)

| Model | Source | Full 5-finger bones? | Face morphs | Size | Notes |
| --- | --- | --- | --- | --- | --- |
| **Kai (selected)** | [VTubeMe](https://vtubeme.com/free-vrm-avatars/kai) | Yes (40) | Yes (66 unique) | 9.34 MB | Full fingers + face |
| Remy | Mixamo pack (HF mirror) | Yes (40) | No | 31 MB | Clear male cartoon; no morphs — fallback in `candidates/remy.glb` |
| Aj | Mixamo pack (HF mirror) | Yes (46) | No | 6.4 MB | Casual male; no morphs |
| Y Bot | Mixamo pack | Yes (40) | No | 2.2 MB | Robot — not a human cartoon |
| Soccer blue | vibeassets | **No (0)** | No | 0.5 MB | Rejected — mitt hands |
| Mousey | Mixamo pack | **No pinky** | No | 31 MB | Rejected — incomplete hands |

Rejected attractive/low-poly packs (Kenney mini characters, Gobkit humans, Vuena blocky) were either unavailable to download here or lack independent finger bones.

## Download pages (if you need to re-fetch)

1. **Kai (preferred):** https://vtubeme.com/free-vrm-avatars/kai — use **Download .glb**, save as `media/avatar/signer.glb`
2. Remy / Aj mirrors: Hugging Face dataset `tanish434/Mixamo-Animations-Characters` → `character_refined_glb/`
