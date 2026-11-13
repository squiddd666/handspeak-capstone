/*
  Global bridge for controlling the app from outside React.
  Exposes a `window.SignSpeak` object with small helpers:
    - navigate(path)
    - getElement(selector)
    - fetchJSON(url, init)
    - queryAPI(url, init)
    - setTheme('light'|'dark')
    - on(event, handler) / off(event, handler) / emit(event, detail)
    - openInNewTab(url)

  This file is intentionally lightweight and framework-agnostic.
*/

declare global {
  interface Window {
    SignSpeak?: any;
  }
}

const SignSpeak = {
  navigate(path: string) {
    try {
      // use history API and notify listeners (React Router will handle popstate)
      window.history.pushState({}, "", path);
      window.dispatchEvent(new PopStateEvent("popstate"));
      return true;
    } catch (e) {
      console.error("SignSpeak.navigate error:", e);
      return false;
    }
  },

  getElement(selector: string) {
    return document.querySelector(selector);
  },

  async fetchJSON(url: string, init?: RequestInit) {
    const res = await fetch(url, init ?? {});
    return await res.json();
  },

  async queryAPI(url: string, init?: RequestInit) {
    // returns parsed JSON when possible, otherwise raw text
    const res = await fetch(url, init ?? {});
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch (e) {
      return text;
    }
  },

  setTheme(theme: "light" | "dark") {
    if (theme !== "light" && theme !== "dark") return false;
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("theme", theme);
    } catch {}
    // allow components to react via a custom event
    window.dispatchEvent(new CustomEvent("SignSpeak:theme", { detail: { theme } }));
    return true;
  },

  on(event: string, handler: EventListenerOrEventListenerObject) {
    // subscribe to custom SignSpeak events: 'someEvent' => 'SignSpeak:someEvent'
    window.addEventListener(`SignSpeak:${event}`, handler as EventListener);
  },

  off(event: string, handler: EventListenerOrEventListenerObject) {
    window.removeEventListener(`SignSpeak:${event}`, handler as EventListener);
  },

  emit(event: string, detail?: any) {
    window.dispatchEvent(new CustomEvent(`SignSpeak:${event}`, { detail }));
  },

  openInNewTab(url: string) {
    window.open(url, "_blank", "noopener,noreferrer");
  },
};

window.SignSpeak = SignSpeak;

export default SignSpeak;
