import { useState, useEffect } from "react";
import Login from "./components/Login";
import SearchPage from "./components/SearchPage";
import { logout } from "./api";
import { getInitialTheme, applyTheme, watchSystemTheme } from "./theme";
import "./index.css";

function App() {
  const [session, setSession] = useState(null);
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    if (theme !== "system") return undefined;
    return watchSystemTheme(() => applyTheme("system"));
  }, [theme]);

  const handleLogin = (data) => setSession(data);
  const handleLogout = async () => {
    try {
      if (session?.token) await logout(session.token);
    } finally {
      setSession(null);
    }
  };

  if (!session) {
    return (
      <Login
        onLogin={handleLogin}
        theme={theme}
        onThemeChange={setTheme}
      />
    );
  }

  return (
    <SearchPage
      session={session}
      onLogout={handleLogout}
      theme={theme}
      onThemeChange={setTheme}
    />
  );
}

export default App;
