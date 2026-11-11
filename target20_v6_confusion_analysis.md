# Target-20 V6 confusion analysis

Development only. This checks source gloss metadata, tracking, crop boundaries and frozen V3 outputs. It is not a causal ablation and does not certify linguistic labels. V6 never produces a score or prediction.

## YES versus YOU
- YES: source gloss YES; V3 top YOU, score 0.991867, accepted YOU. Legacy crop 17/37 frames; largest legacy motion at visibility transition: True.
- YOU: source gloss YOU; V3 top BAD, score 0.573823, accepted none. Legacy crop 16/48 frames; largest legacy motion at visibility transition: True.
- V5 archival validation (not a V6 trial): YES top YOU, score 0.995771, accepted YOU.
- Single-clip V6 encoder comparison (may use tagged V5 payload for tracker dropout): {'joint_hand_mask_agreement': 0.171875, 'jointly_visible_hand_xy_mae': None}. Descriptive only; overlap does not establish class equivalence.

## GOOD versus EAT
- GOOD: source gloss GOOD; V3 top EAT, score 0.973961, accepted none. Legacy crop 16/54 frames; largest legacy motion at visibility transition: True.
- EAT: source gloss EAT2; V3 top SORRY, score 0.76753, accepted none. Legacy crop 15/39 frames; largest legacy motion at visibility transition: True.
- V5 archival validation (not a V6 trial): GOOD top EAT, score 0.985965, accepted EAT.
- Single-clip V6 encoder comparison (may use tagged V5 payload for tracker dropout): {'joint_hand_mask_agreement': 1.0, 'jointly_visible_hand_xy_mae': 0.4602228628933517}. Descriptive only; overlap does not establish class equivalence.

## WHO versus PLEASE
- WHO: source gloss WHO; V3 top not observed, score not observed, accepted none. Legacy crop 16/42 frames; largest legacy motion at visibility transition: True.
- PLEASE: source gloss PLEASE; V3 top HELP, score 0.492132, accepted none. Legacy crop 16/37 frames; largest legacy motion at visibility transition: True.
- V5 archival validation (not a V6 trial): WHO top PLEASE, score 0.977223, accepted PLEASE.
- Single-clip V6 encoder comparison (may use tagged V5 payload for tracker dropout): {'joint_hand_mask_agreement': 0.234375, 'jointly_visible_hand_xy_mae': 0.26340065921351985}. Descriptive only; overlap does not establish class equivalence.

No metadata mismatch is inferred merely from a wrong prediction. The listed legacy crop peaks and mask disagreement provide evidence of potential distortion, not proof that fixing them would change V3 output. Small class-level development counts limit claims about signer/variant diversity; model limitations and distribution shift remain plausible. No thresholds were changed.
