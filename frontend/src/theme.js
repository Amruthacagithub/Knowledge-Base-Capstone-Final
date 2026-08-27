const THEME_KEY = "ekip-theme";

export function resolveTheme(preference) {
  if (preference === "light" || preference === "dark") return preference;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function getInitialTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") return stored;
  return "system";
}

export function applyTheme(preference) {
  const resolved = resolveTheme(preference);
  document.documentElement.setAttribute("data-theme", resolved);
  localStorage.setItem(THEME_KEY, preference);
  return resolved;
}

export function watchSystemTheme(onChange) {
  const mq = window.matchMedia("(prefers-color-scheme: light)");
  const handler = () => onChange(resolveTheme("system"));
  mq.addEventListener("change", handler);
  return () => mq.removeEventListener("change", handler);
}
