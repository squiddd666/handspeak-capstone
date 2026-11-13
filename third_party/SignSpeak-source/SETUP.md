# SignSpeak Setup & Run Instructions

All AI runs on-device — there is no server to set up.

## ✅ Quick Start (Laptop)

Requires **Node.js 18+** ([nodejs.org](https://nodejs.org)).

```powershell
.\start.bat
```

The script will:
- Install dependencies on first run
- Build the app if needed
- Start a local server at `http://localhost:4173`
- Open your browser automatically
- Press `Ctrl+C` to stop

Or try it with zero setup: **https://sign-speak-rho.vercel.app**

## 📱 Android

Install [SignSpeak-debug.apk](SignSpeak-debug.apk) on your phone (enable
"Install unknown apps" when prompted, allow camera on first launch).

To rebuild the APK (needs JDK 17+ and the Android SDK):

```powershell
cd web
npm install
npm run build
npx cap sync android
cd android
.\gradlew assembleDebug
# APK appears at web/android/app/build/outputs/apk/debug/app-debug.apk
```

## 🔧 Development Mode (Hot Reload)

```powershell
cd web
npm install
npm run dev:frontend
```

Open `http://localhost:8080`. Edits to `web/src/` reload instantly.
Run `npm run build` when done to refresh the production build.

---

## 🔧 Troubleshooting

**"Node.js / npm not found"**
- Install Node.js 18+ from [nodejs.org](https://nodejs.org) and re-run `start.bat`

**Port 4173 already in use**
- `start.bat` detects an already-running SignSpeak and just opens the browser.
  If some other app owns the port: `netstat -ano | findstr :4173` then `taskkill /PID <PID> /F`

**Camera permission denied**
- Allow camera access when the browser or Android prompts. On Android:
  Settings → Apps → SignSpeak → Permissions → Camera

**Predictions feel off**
- Good, even lighting on your hand matters most. Retrain with your own
  samples via `trainer/` if needed (see README).

---

Made with ❤️ for accessible communication
