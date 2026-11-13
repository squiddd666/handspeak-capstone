# OpenHands 100-word local reference test

- **Top-1: 70/100 (70.0%)**
- **Top-5: 83/100 (83.0%)**
- **Capture/download failures: 0**
- 100 unique supported labels, one clip per word.
- Previous local reference clips: 9/31 top-1 correct (reused unchanged).
- Newly downloaded dictionary references: 61/69 top-1 correct.
- Model weights unchanged; SHA-256 verified after evaluation.

This is a mixed-source convenience-set reference test, not an independent
benchmark, signer-independent test, or live webcam accuracy measurement.
Dictionary clips may overlap WLASL/OpenHands training. Sign variants and
meanings have not been independently verified by an ASL expert. A high score
on these references does not establish generalization to new users. No model
training or threshold tuning was performed.

## Correct words

ACCIDENT, AFRICA, APPLE, BASKETBALL, BEFORE, BIRD, BIRTHDAY, BLACK, BLUE, BOWLING, BROWN, CANDY, CHANGE, CHEAT, CITY, COLOR, COMPUTER, CORN, COUSIN, COW, DANCE, DARK, DEAF, DECIDE, DOCTOR, DOG, DRINK, EAT, ENJOY, FAMILY, FISH, FORGET, FULL, GIVE, GRADUATE, HAT, HEARING, JACKET, KISS, LANGUAGE, LAST, LETTER, MANY, MEDICINE, MEET, NOW, ORANGE, PAINT, PINK, PLAY, PULL, PURPLE, RIGHT, SAME, SCHOOL, SECRETARY, SHIRT, SHORT, SON, TELL, THANKSGIVING, THIN, THURSDAY, TIME, WALK, WANT, WHITE, WOMAN, WRONG, YEAR.

## Incorrect words

ALL, BED, BOOK, BUT, CAN, CHAIR, CLOTHES, COOK, COOL, FINE, FINISH, GO, HELP, HOT, HOW, LATER, LIKE, MAN, MOTHER, NEED, NO, PAPER, PIZZA, STUDY, TABLE, TALL, WHAT, WHO, WORK, YES.

## Reproducibility

Upstream commit: 6219c4d5d017457da220ff3037ea209c739fd663.
Unmodified pretrained checkpoint; stored validation result 69.1588785046729%.
Upstream preprocessing, base plus 8 TTA passes, fixed seeds 42.
A no-hand safeguard exists in the harness; no no-hand failures occurred here.

Full results: all100-results.json / all100-results.csv.
Original 31-clip report: reference-results-31.json.
Downloaded clips: reference-videos/ (local testing, not redistributed).
URL availability and download metadata: ../openhands-reference-videos.json,
download-manifest.json. All per-clip hashes/source URLs are in the JSON report.
Evaluation logs: all100.stdout.log / all100.stderr.log.

Run: .\.venv\Scripts\python.exe openhands-test/evaluate100.py
View: http://localhost:8001 (Reference-video evaluation section).
