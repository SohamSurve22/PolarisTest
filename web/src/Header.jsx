const NAV = [
  { id: "dashboard", label: "Dashboard" },
  { id: "documents", label: "Documents" },
  { id: "parser", label: "Parser" },
  { id: "graph", label: "Knowledge Graph" },
  { id: "validation", label: "Validation", current: true },
  { id: "queries", label: "Queries" },
];

export default function Header({ theme, onToggleTheme }) {
  return (
    <nav className="top-nav" aria-label="Primary">
      <div className="top-nav-left">
        <p className="wordmark">PolarisLex</p>
        <div className="top-nav-links">
          {NAV.map((item) =>
            item.current ? (
              <span key={item.id} className="nav-link is-current">
                {item.label}
              </span>
            ) : (
              <span key={item.id} className="nav-link is-idle">
                {item.label}
              </span>
            ),
          )}
        </div>
      </div>
      <div className="top-nav-right">
        <button
          className="icon-btn"
          type="button"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          onClick={onToggleTheme}
        >
          <span className="material-symbols-outlined">
            {theme === "dark" ? "light_mode" : "dark_mode"}
          </span>
        </button>
        <div className="avatar" aria-hidden="true">
          P
        </div>
      </div>
    </nav>
  );
}
