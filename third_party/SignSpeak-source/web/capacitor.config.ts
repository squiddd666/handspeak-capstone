import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.medhu.signspeak",
  appName: "SignSpeak",
  // The vite build outputs to ../frontend (shared with the desktop backend).
  webDir: "../frontend",
  android: {
    // Camera (getUserMedia) requires a secure context; Capacitor's default
    // https://localhost scheme provides one.
    allowMixedContent: false,
  },
};

export default config;
