import { applyTheme, resolveTheme } from "../theme";

export default function ThemeToggle({ theme, onThemeChange }) {
  const resolved = resolveTheme(theme);

  const toggle = () => {
    const next = resolved === "dark" ? "light" : "dark";
    applyTheme(next);
    onThemeChange(next);
  };

  let label = resolved === "dark" ? "Light mode" : "Dark mode";
  if (theme === "system") {
    label = `Theme (${resolved})`;
  }

  return (
    <button
      type="button"
      className="header-btn theme-toggle-btn"
      onClick={toggle}
      title={label}
      aria-label={label}
    >
      <span aria-hidden="true">{resolved === "dark" ? "☀" : "☾"}</span>
      <span className="theme-toggle-label">{resolved === "dark" ? "Light" : "Dark"}</span>
    </button>
  );
}
