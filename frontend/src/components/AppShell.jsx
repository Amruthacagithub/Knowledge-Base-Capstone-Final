export default function AppShell({
  sidebar,
  main,
  panel,
  header,
  panelOpen,
  navigationOpen = false,
  onCloseNavigation,
}) {
  return (
    <div
      className={`app-shell ${panelOpen ? "sources-open" : "sources-closed"} ${
        navigationOpen ? "navigation-open" : "navigation-closed"
      }`}
    >
      {header}
      <div className="shell-body">
        {sidebar}
        <main className="shell-main">{main}</main>
        {panelOpen && panel}
      </div>
      {navigationOpen && (
        <button
          type="button"
          className="navigation-backdrop"
          aria-label="Close navigation"
          onClick={onCloseNavigation}
        />
      )}
    </div>
  );
}
