# Kai signing clips

Watch & practice now prioritizes the matching
[`../reference/`](../reference/README.md) video reconstruction when one is
available. This folder retains captured/authored fallbacks; an unrelated
performance is no longer paired as the default animation beside a local video.

HELLO, PLEASE, BYE, MY, BROTHER and BUY use captured body, wrist and finger motion from
[Studio Galt's Sign Language Mocap Archive](https://github.com/StudioGalt/Sign-Language-Mocap-Archive).
The original motion is **CC0-1.0**; see [the source license](SOURCE-LICENSE.md).
Kai's model remains separately licensed **CC BY 4.0** and is not replaced or re-exported.

FISH, PAIN, SEE, SICK and NIGHT additionally have Kai-native **hand-authored
approximations**, not captured Studio Galt performances. See the authored section below.

## Included motions

| Sign | Source publication | Frames after calibration | Duration | Tracks |
| --- | --- | --- | --- | --- |
| HELLO | 2024-06-09 | 2–133 | 2.183 seconds | 43 |
| PLEASE | 2024-10-13 | 2–124 | 2.033 seconds | 43 |
| BYE | 2024-09-07 | 2–180 | 2.967 seconds | 43 |
| MY | 2024-06-09 | 2–80 | 1.300 seconds | 43 |
| BROTHER | 2024-08-05 | 2–209 | 3.450 seconds | 43 |
| BUY | 2024-09-05 | 2–193 | 3.183 seconds | 43 |

All use the archive's **Game Ready / No Mesh Mixamo FBX**, sampled at 60 fps.
Each GLB contains animation nodes and quaternion tracks only, not another avatar.
All thirty weighted finger joints, both wrists, arms, torso and head are mapped.
Locomotion, leg animation and source mesh/face shapes are not imported.
The first FBX frame is a calibration/T-pose and is omitted from playback.

Body rotations use aligned world-space rest-pose correction. Wrists and fingers
use anatomical palm/finger frames to compensate for the two rigs' different
bone axes and Kai's curled/fanned bind fingers. Directly copying FBX Euler angles
or retaining those bind curls would distort handshapes.
Captured wrist paths are mapped relative to the head and scaled by torso length;
an offline two-bone IK bake adapts Kai's arm lengths and keeps hands clear of the
face/chest. The web player still uses quaternion tracks only, without runtime IK.
Elbow planes are mapped relative to the source shoulder, not as head-relative
points. For nearly straight source arms, small inward bends would be amplified
by Kai's different limb proportions and fold the elbows into the torso. An
outward, slightly backward anatomical pole is used below 15° source elbow
flexion and smoothly blends into the captured plane by 35°. Initial/finished
arms-down poses are checked for torso clearance and unchanged limb lengths.
Elbow-pole direction changes are capped at 8° per 60 fps sample to avoid flips
near a straight arm; this does not change the captured wrist target path.
BROTHER and BUY have fast captured finger releases (peak local steps of about
30.69° and 32.43° per sample). These were checked against the original FBXs and
are preserved, not mistaken for an IK flip or replaced by procedural handshapes.
The corresponding joint/frame measurements are recorded in the source manifest.

The upstream BROTHER ReadMe appears to contain stale Bow Archery/date fields.
Selection uses the pinned BROTHER FBX filename and hash, not those stale fields;
the head-to-two-hand motion was visually checked on Kai. This is not independent
linguistic validation: use the linked lesson to review handshape/contact details.

`index.json` records source paths, hashes, frame ranges, the Kai model hash and
retargeting metadata. The upstream commit is pinned to
`4bc88392a40cb93a5850eb1ebe63d41f68677032`; no mutable-branch downloads are used.

## Playback

Retargeted clips take priority over hand-authored gestures where both exist.
Captured fingers are not overwritten by procedural handshape approximations.
Mocap uses its own recorded timeline rather than being stretched to the unrelated
PopSign reference video. Speed, pause, repeat and replay still work. Existing
authored words, including HELLO/PLEASE, retain their fallback if mocap cannot load.
The four new words require their bundled clips; a different sign is never used
as a substitute when an asset is missing.

**BYE, MY, BROTHER and BUY are 3D learning examples only.** They appear in the
"New captured ASL words" group, have explicit learning-only badges, and do not
enable or claim new camera-recognition models. Camera practice is hidden for
these buttons. BROTHER has an existing, separately credited reference video;
BYE, MY and BUY display a clean Kai-only view with an external lesson link.

## Complete Watch & practice coverage

All **47 currently listed words** have a Kai demo: six captured Studio Galt
motions and 41 hand-authored approximations (36 active legacy JavaScript gestures
and the five new Kai-native GLBs below). This does not expand the separate
201-word vocabulary or train any new camera-recognition models.

| Authored sign | Kai motion | Duration |
| --- | --- | --- |
| FISH | Upright flat hand swimming sideways with alternating wrist turns | 3.1 seconds |
| PAIN | Index-only hands approach each other and twist (general PAIN/HURT) | 3.0 seconds |
| SEE | V-hand near the eye, then moving forward | 2.8 seconds |
| SICK | Bent middle fingers indicate forehead and stomach | 2.8 seconds |
| NIGHT | Flat dominant hand descends over a horizontal support hand | 2.9 seconds |

`*-kai-authored.glb` files contain 43 Kai-native rotation tracks at 60 fps,
including all thirty weighted finger joints. Their word-specific wrist paths and
palm orientations are authored in `scripts/author_kai_practice.py`. Frozen
CC0 static poses from HELLO and BROTHER supply bind-compatible finger/rest
templates; V-hand spreads and bent-middle shapes are modified anatomically.
Left handshapes are mirrored by anatomical directions, not by copying right-hand
local rotations. Template files, hashes and single-frame samples are recorded
separately in each entry's `source.staticPoseTemplates`.

**Those static templates do not make the new word motions captured mocap.**
Their source kind is `authored`, their provenance is project-authored, and the
player explicitly says **Kai hand-authored approximation**. They are not traced
from or frame-matched to the research videos, and may use different sign variants
(including two-handed PAIN/SICK). Check the reference or linked ASL University
lesson for precise handshape, contact and facial grammar. The existing experimental
camera previews and recognition accuracy for these five words are unchanged.

Eased quaternion interpolation and offline two-bone IK preserve Kai's arm
lengths. Elbows stay outside the torso, and every authored clip starts and finishes
in the same safe neutral pose for repeat; pausing holds the current pose. Like captured clips, these
GLBs keep their own timing and native fingers rather than taking a procedural
overlay from an unrelated video. Replay uses the selected word; stale availability
or reference-video callbacks cannot restart playback after leaving the preview.

These assets change the **3D demonstration**, not the recognition models or their
measured accuracy. Source motion and retargeted hand/contact positions should be
reviewed before treating the preview as precise instruction. Facial ASL grammar
is not transferred by these mesh-free FBXs.

## Reproduce / extend

Use ordinary Python to fetch the small, pinned subset, then Blender 4.5+ to bake:

```powershell
python scripts/fetch_studio_galt.py
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python scripts/retarget_studio_galt.py --
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python scripts/author_kai_practice.py --
node --test training/test_kai_mocap.mjs training/test_watch_practice.mjs
python -X utf8 -m unittest training.test_kai_mocap_http
```

Raw FBXs are cached outside the served website, under
`%LOCALAPPDATA%/HandSpeak/mocap-cache/studio-galt/<commit>` (or `~/.cache/handspeak`
on other systems). Neither the roughly 46 GB archive nor the Galtis mesh is needed.
To add a sign, add its correctly labelled, pinned source and hashes to
`scripts/studio-galt-sources.json`, fetch and rebake, then review the result.
Do not relabel a different sign just because its movement looks similar.
After changing/rebaking the captured template clips, rebake the authored clips
as well so their recorded template hashes remain current.

The Node tests verify asset hashes, Kai bind axes, neutral-pose elbow clearance,
fixed limb lengths, native finger tracks, timing,
clip priority, failed-load fallbacks, asynchronous sign switching, learning-only
UI labels and reference-video handling. An optional
`HANDSPEAK_THREE_PACKAGE` environment variable pointing to an unpacked official
`three@0.160.0` package also checks the real GLTFLoader/AnimationMixer bindings,
manual scrubbing and held pause/end poses. HTTP tests check GLB MIME types and
that private project files remain blocked; they never initialize a database.
Coverage tests derive the 47 buttons from the actual HTML and enabled catalog,
exercise every playback ID, and check the new gestures' distinctive finger/path
features, whole-clip arm lengths/clearance and safe first/final poses.
