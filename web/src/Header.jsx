const NAV = [
  { id: "dashboard", label: "Dashboard" },
  { id: "documents", label: "Documents" },
  { id: "parser", label: "Parser" },
  { id: "graph", label: "Knowledge Graph" },
  { id: "validation", label: "Validation", tab: true },
  { id: "queries", label: "Queries", tab: true },
];

export default function Header({ theme, onToggleTheme, tab, onTab, onGoLanding }) {
  return (
    <nav className="top-nav" aria-label="Primary">
      <div className="top-nav-left">
        <p className="wordmark" style={{ cursor: "pointer" }} onClick={onGoLanding}>
          PolarisLex
        </p>
        <div className="top-nav-links">
          {onGoLanding && (
            <button
              type="button"
              className="nav-link"
              onClick={onGoLanding}
            >
              ← Landing Page
            </button>
          )}
          {NAV.map((item) =>
            item.tab ? (
              <button
                key={item.id}
                type="button"
                className={`nav-link${tab === item.id ? " is-current" : ""}`}
                aria-current={tab === item.id ? "page" : undefined}
                onClick={() => onTab(item.id)}
              >
                {item.label}
              </button>
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
