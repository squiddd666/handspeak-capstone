<div align="center">

# ✋ SignSpeak

### AI-Powered Real-Time American Sign Language Interpreter

![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0F9D58?style=for-the-badge&logo=google&logoColor=white)
![ONNX](https://img.shields.io/badge/ONNX_Runtime-5C2D91?style=for-the-badge&logo=onnx&logoColor=white)
![Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)

**Decode sign language in real-time using just your camera — all AI runs on YOUR device. No server, no internet, no special hardware.**

### 🌐 [Try it live → sign-speak-rho.vercel.app](https://sign-speak-rho.vercel.app)

📱 [Download the Android APK](SignSpeak-debug.apk) · 🏆 [Devpost](https://devpost.com/software/signspeak-kceyum)

</div>

---

## 🎯 What is SignSpeak?

SignSpeak is a real-time ASL (American Sign Language) alphabet interpreter that uses your camera and on-device AI to translate hand gestures into text. Every bit of machine learning — hand tracking and letter classification — runs locally in your browser or phone. Nothing is ever uploaded.

### 🧩 Three Modes

| Mode | Description |
|------|-------------|
| **🔤 Live Interpreter** | Spell out letters in real-time. Hold a sign steady for 2s to auto-add it (or tap **Add**), and letters combine into words with smart debouncing. |
| **🎓 Practice Trainer** | Pick a letter from the guide, see the reference sign, and hold the gesture for 5s until the AI confirms you've got it. |
| **🎮 Hangman Game** | Classic hangman — but you guess letters by signing them. 6 lives, 2 hints per round. |

---

## ⚙️ How It Works

```
┌────────────┐   MediaPipe Tasks    ┌─────────────┐    ONNX Runtime    ┌───────────┐
│   Camera    │ ──── (GPU/wasm) ──▶ │ 21 landmarks │ ──── (wasm) ─────▶ │ LSTM model │
│  (in-app)   │                     │  normalized  │   30-frame window  │  A–Z + %   │
└────────────┘                     └─────────────┘                    └───────────┘
                        everything happens on YOUR device
```

1. **Camera** frames are processed at 30 FPS — entirely in the browser / WebView
2. **MediaPipe Hand Landmarker** (GPU-accelerated) extracts 21 hand landmarks per frame
3. Landmarks are **normalized** (wrist-centered, scale-invariant) and buffered into 30-frame sequences
4. A custom-trained **LSTM** (275 KB, exported to ONNX) classifies the sequence into A–Z letters
5. **Debouncing** commits a letter only after a 2-second steady hold at ≥85% confidence

---

## 🚀 Three Ways to Run It

### 1. Web — zero install
Open **[sign-speak-rho.vercel.app](https://sign-speak-rho.vercel.app)** and allow camera access. Works on desktop and mobile browsers.

### 2. Laptop — fully offline
```powershell
git clone https://github.com/medhu0505/SignSpeak.git
cd SignSpeak
.\start.bat
```
`start.bat` installs dependencies, builds the app, starts a local server, and opens your browser automatically. Requires Node.js 18+. Kill your Wi-Fi after loading — it keeps working.

### 3. Android — native app
Install **[SignSpeak-debug.apk](SignSpeak-debug.apk)** (23 MB) on any Android phone — enable "Install unknown apps" when prompted, grant camera access on first launch. 100% offline.

To rebuild the APK yourself:
```powershell
cd web
npm install
npm run build
npx cap sync android
cd android
.\gradlew assembleDebug   # needs JDK 17+ and the Android SDK
```

---

## 📁 Project Structure

```
SignSpeak/
├── web/                       # The app (single source of truth)
│   ├── src/
│   │   ├── engine/            # On-device AI engine: landmarks, ONNX predictor,
│   │   │                      #   decoder / practice / hangman session logic
│   │   ├── pages/             # Home, Interpreter, Guide, Practice, Hangman
│   │   ├── components/        # UI components (shadcn/ui) + ErrorBoundary
│   │   └── lib/               # Camera loop, landmark overlay
│   ├── public/
│   │   ├── models/            # asl.onnx (LSTM) + hand_landmarker.task (MediaPipe)
│   │   ├── wasm/              # MediaPipe wasm runtime
│   │   └── assets/reference/  # ASL reference images (A–Z)
│   └── android/               # Capacitor Android project (APK wrapper)
├── trainer/                   # Model training pipeline (Python)
│   ├── capture.py             # Record hand landmark sequences from webcam
│   ├── train.py               # Train the LSTM classifier (PyTorch)
│   └── export_onnx.py         # Export asl.pt → asl.onnx for the browser
├── backend/                   # Legacy FastAPI server (optional — no longer needed)
├── vercel.json                # Vercel build config + SPA rewrites
├── SignSpeak-debug.apk        # Ready-to-install Android build
└── start.bat                  # One-click laptop launcher
```

---

## 🏋️ Training Your Own Model

```bash
pip install -r trainer/requirements.txt

cd trainer
python capture.py          # A–Z picks a letter, SPACE records, B = burst mode
python train.py --epochs 50
python export_onnx.py      # exports to web/public/models/asl.onnx
```

Then rebuild the app (`npm run build` in `web/`) — the new model ships everywhere: web, laptop, and APK.

---

## 🎛️ Configuration

| Setting | Location | Default |
|---------|----------|---------|
| Confidence threshold | `web/src/engine/base.ts` | `0.85` |
| Hold-to-commit time | `web/src/engine/base.ts` | `2000 ms` |
| Sequence length | `web/src/engine/predictor.ts` | `30 frames` |
| Auto-space timeout | `web/src/engine/decoder.ts` | `5.0 s` |
| Practice hold time | `web/src/engine/practice.ts` | `5.0 s` |
| Hangman lives / hints | `web/src/engine/hangman.ts` | `6 / 2` |
| Auto word-log (idle hand) | `web/src/pages/Interpreter.tsx` | `2.5 s` |

---

## 🛠️ Tech Stack

- **App**: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **On-device AI**: MediaPipe Tasks Vision (hand tracking, GPU delegate) + ONNX Runtime Web (LSTM inference)
- **Training**: PyTorch + MediaPipe + OpenCV
- **Android**: Capacitor 8 (WebView wrapper + camera permission bridge)
- **Hosting**: Vercel (auto-deploys from `main`)

---

<div align="center">

**Works 100% offline · Real-time gesture detection · Private by design — video never leaves your device**

Made with ❤️ for accessible communication

</div>
