import { createRoot } from "react-dom/client";
// Self-hosted Poppins (matches the weights previously loaded from Google Fonts)
// so the app renders identically offline / inside the Android WebView.
import "@fontsource/poppins/300.css";
import "@fontsource/poppins/400.css";
import "@fontsource/poppins/500.css";
import "@fontsource/poppins/600.css";
import "@fontsource/poppins/700.css";
import App from "./App.tsx";
import "./index.css";
import "./root.ts";
//let videlement = document.getElementById("VideoFeed")
//function updateCameraFeed() {
  //videlement.src = "http://127.0.0.1:5000/video?" + new Date().getTime();
//}
createRoot(document.getElementById("root")!).render(<App />);
