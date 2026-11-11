# Pretrained word vocabulary

Source: **PopSign ASL v1.0**, game category, by Thad Starner, Sean Forbes,
Matthew So, David Martin, Rohit Sridhar, Gururaj Deshpande, Sam Sepah,
Sahir Shahryar, Khushi Bhardwaj, and collaborators (2023).

- Dataset and download guide: https://signdata.cc.gatech.edu/view/guides/downloading_popsign/index.html
- Author paper and dataset license statement: https://signdata.cc.gatech.edu/res/doc/popsign_v1_0/popsign_v1_0.pdf
- License: **Creative Commons Attribution 4.0 International** — https://creativecommons.org/licenses/by/4.0/

Changes: Selected a small subset of the original labeled video archive; extracted
MediaPipe hand coordinates, removed untracked lead-in/end frames, interpolated
short internal tracking gaps, corrected for image aspect ratio, normalized positions,
centered movements over all usable frames, selected a dominant continuous run
when it contains at least 70% of usable frames, and resampled to 20 frames.
Recognition uses coordinate templates. Six separate compressed video examples are
bundled in `media/signs/` for the learning player, with their own credits and provenance.
This project and its evaluation are not endorsed by the dataset authors.

Included words: HELLO, THANK YOU, PLEASE, YES, NO, FINISH.
DRINK is reserved as an unsupported-word check, not a training class.

Original training, validation, and test partitions are preserved. Participant IDs
are checked for overlap. Validation selects rejection thresholds; test examples
are not used as templates. `asl-words-evaluation.json` records sample counts,
tracking exclusions, the small-subset results, and limitations. These results are
not a benchmark of continuous ASL translation or live-camera accuracy.

## Optional expanded-word preview

DRINK, WATER, and BOOK use 86 additional training-only coordinate references (31, 30, and 25 respectively). This preview is disabled by default because it adds false suggestions. The original six-word model is evaluated first; extra words are considered only when it rejects. Training and validation/test participants are disjoint. Thresholds were chosen using validation; the preview configuration was frozen before evaluating new test recordings.

In the new-word test, 9/24 clips were correct, 7 were incorrectly labeled, and 8 had no match. Existing-word regression results remained 20/36 correct with no wrong labels. Combined real/synthetic negative false suggestions rose from 23/40 to 27/40. See `asl-extra-words-evaluation.json` and `asl-extra-words-sources.json`. The previously unsupported DRINK label remains an unsupported check for the original model only; expanded-model negatives use APPLE and MILK plus synthetic movement.

## Sentence vocabulary preview (v6)

Added FOOD, HUNGRY, LIKE, GO to the optional expanded vocabulary, with 59 usable training references from 96 selected clips. Original six-word default remains unchanged. The preview compares all labels and lets a qualified new-label match take priority. New test recognition was 5/24 (FOOD 1/6, HUNGRY 2/6, LIKE 2/6, GO 0/6); existing-word correct/wrong stayed 29/7 out of 60 regression clips; unsupported false suggestions increased 24→26 out of 40. No default promotion. See `asl-extra-words-evaluation.json` and `reports/vocabulary-v6` for protocol and limitations. Videos are attributed PopSign training examples, not independent evidence of accuracy.


## Requested category library

The 200-entry catalog links to PopSign and ASLU/Lifeprint lessons, while clearly distinguishing related-word lessons from full-phrase examples. External lessons are not rehosted. Downloadable PopSign v1.0 source data was available for 49 requested labels; v2.1 archive requests returned 404 during collection. No missing sign is silently substituted with another training label. Explicit lexical aliases such as GRANDMOTHER/grandma and CALL/callonphone are documented in the catalog.

The first category models contain 48 usable requested labels in 14 research groups. They are withheld from the live site after failing accuracy and automatic-capture checks. See [category evaluation](motion-categories/evaluation.json). These previews do not establish high accuracy, and the original six-word default remains separate. Further dense-frame recovery outcomes are documented in the repository reports.

Practice-video credits and original/derived checksums: [video credits](../media/signs/README.md), [new example provenance](../media/signs/catalog-sources.json). Models and derived templates use PopSign ASL v1.0, Georgia Tech and DPAN, CC BY 4.0.
