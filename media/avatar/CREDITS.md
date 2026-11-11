# Avatar credits

## 3D signer (Watch & Practice)

- **Model:** [Kai](https://vtubeme.com/free-vrm-avatars/kai) by [VTubeMe](https://vtubeme.com)
- **File:** `signer.glb` (exported GLB from the Kai VRM pack)
- **License:** [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **Attribution:** Include “Kai by VTubeMe” with a link to https://vtubeme.com/free-vrm-avatars/kai

## Reference videos

PopSign ASL v1.0 and ASL Citizen research clips used as silent reference videos are credited in [`media/signs/README.md`](../signs/README.md).

## Motion

`reference/*-reference.glb` reconstruct the exact bundled PopSign/ASL Citizen
reference performance for video-backed Watch & practice words. They are estimated
monocular reconstructions, not Studio Galt captures. Source paths/hashes and
tracking-gap metadata are in `reference/index.json`. These derived motions retain
the respective reference dataset's terms, including ASL Citizen research-use
restrictions; they are not newly licensed CC0. See `reference/README.md`.

Retained fallback clips for HELLO, PLEASE, BYE, MY, BROTHER and BUY use Studio Galt's **CC0-1.0** ASL mocap,
retargeted onto Kai. BYE, MY, BROTHER and BUY are 3D learning examples only.
Source files, the pinned upstream commit, hashes and reproduction instructions are
recorded in [`clips/README.md`](clips/README.md) and [`clips/index.json`](clips/index.json).
This does not change Kai's separate CC BY 4.0 attribution requirement.

FISH, PAIN, SEE, SICK and NIGHT use **project-authored approximations**, not
Studio Galt captured performances. Frozen CC0 static hand/rest templates from
the verified HELLO and BROTHER clips are adapted with authored paths, palm
orientations, V-hand spreads and bent-middle shapes. Static template provenance
and hashes are recorded separately in each authored clip's index entry.
No reference-video motion was extracted to produce these new clips.

Legacy `media/avatar/baked/`, `hand_cleanup/`, or other animations derived from
the research reference recordings follow those datasets' terms. These limitations
do not apply to the Studio Galt CC0 clips listed above.
