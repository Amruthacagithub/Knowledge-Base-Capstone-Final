export default function Topbar({ onLogout }) {
  return (
    <header className="topbar shell-header">
      <div className="brand">
        <span className="mark">T</span>
        <span className="brand-product">TechNova</span>
        <span className="brand-context">Knowledge Base</span>
      </div>
      <div className="topbar-right">
        {onLogout ? (
          <button type="button" className="logout-btn" onClick={onLogout}>
            Sign out
          </button>
        ) : null}
      </div>
    </header>
  );
}
