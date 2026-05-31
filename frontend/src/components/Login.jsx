import { useState } from "react";
import { login } from "../api";
import ThemeToggle from "./ThemeToggle";

const DEMO_USERS = [
  { email: "amrutha@company.com", name: "Amrutha", department: "HR", role: "HR Specialist" },
  { email: "harshini@company.com", name: "Harshini", department: "Engineering", role: "Engineer" },
  { email: "tanvi@company.com", name: "Tanvi", department: "Sales", role: "Sales" },
  { email: "bhaskar@company.com", name: "Bhaskar", department: "Engineering", role: "Admin" },
  { email: "arijith@company.com", name: "Arijith", department: "HR", role: "Employee" },
];

const DEMO_LOGIN_ENABLED = import.meta.env.VITE_DEMO_LOGIN_ENABLED === "true";

function isValidEmail(value) {
  if (!value || value.length > 320 || /\s/.test(value)) return false;
  const at = value.indexOf("@");
  if (at <= 0 || at !== value.lastIndexOf("@")) return false;
  const dot = value.lastIndexOf(".");
  return dot > at + 1 && dot < value.length - 1;
}

export default function Login({ onLogin, theme, onThemeChange }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  const signIn = async (emailToUse, passwordToUse = password) => {
    const trimmed = emailToUse.trim().toLowerCase();
    if (!isValidEmail(trimmed)) {
      setError("Enter a valid work email address.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await login(trimmed, passwordToUse);
      onLogin(data);
    } catch (err) {
      setError(err.message || "Sign in failed. Use a demo email below.");
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = (e) => {
    e.preventDefault();
    signIn(email, password);
  };

  return (
    <div className="login-page-split">
      <div className="login-brand-panel">
        <div className="login-brand-inner">
          <div className="app-name large">
            <span className="mark">T</span>
            <span>TechNova</span>
          </div>
          <h1 className="login-headline">Company knowledge, one search away</h1>
          <p className="login-lead">
            Search HR policies, engineering runbooks, and sales playbooks with
            AI answers grounded in your documents — with role-based access built in.
          </p>
          <ul className="login-features">
            <li>Hybrid search across 58 internal documents</li>
            <li>Cited answers you can verify in source</li>
            <li>Permissions enforced by department and role</li>
          </ul>
          <div className="login-stats">
            <div>
              <strong>250+</strong>
              <span>Employees</span>
            </div>
            <div>
              <strong>3</strong>
              <span>Departments</span>
            </div>
            <div>
              <strong>99.9%</strong>
              <span>Uptime SLA</span>
            </div>
          </div>
        </div>
      </div>

      <div className="login-form-panel">
        <div className="login-form-top topbar-right">
          <ThemeToggle theme={theme} onThemeChange={onThemeChange} />
        </div>

        <div className="login-form-inner">
          <h2>Sign in</h2>
          <p className="login-form-sub">Use your TechNova work credentials to continue</p>

          <form onSubmit={handleContinue} className="login-email-form">
            <label htmlFor="work-email">Work email</label>
            <input
              id="work-email"
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              disabled={loading}
            />
            {!DEMO_LOGIN_ENABLED && (
              <>
                <label htmlFor="work-password">Password</label>
                <input
                  id="work-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  disabled={loading}
                />
              </>
            )}
            <button
              type="submit"
              className="login-primary-btn"
              disabled={loading || !email.trim() || (!DEMO_LOGIN_ENABLED && !password)}
            >
              {loading ? "Signing in…" : "Continue"}
            </button>
          </form>

          {error && <div className="login-error">{error}</div>}

          {DEMO_LOGIN_ENABLED && (
            <>
              <div className="login-divider">
                <span>Demo access for evaluation</span>
              </div>

              <button
                type="button"
                className="login-demo-toggle"
                onClick={() => setShowDemo(!showDemo)}
              >
                {showDemo ? "Hide demo accounts" : "Show demo accounts"}
              </button>

              {showDemo && (
                <div className="demo-user-grid">
                  {DEMO_USERS.map((u) => (
                    <button
                      key={u.email}
                      type="button"
                      className="demo-user-chip"
                      onClick={() => signIn(u.email, "")}
                      disabled={loading}
                    >
                      <span className={`initials ${u.department.toLowerCase()}`}>
                        {u.name.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="demo-chip-text">
                        <span className="demo-chip-name">{u.name}</span>
                        <span className="demo-chip-role">{u.role}</span>
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <footer className="login-footer">
          © TechNova Inc. · Internal use only
        </footer>
      </div>
    </div>
  );
}
