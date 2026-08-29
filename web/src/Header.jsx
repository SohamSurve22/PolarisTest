export default function Header({
  theme,
  onToggleTheme,
  workspace,
  fileName,
  onLoadPolicy,
}) {
  return (
    <header className="site-header">
      <div className="brand">
        <p className="wordmark">PolarisLex</p>
        {workspace ? (
          <p className="subtitle">{fileName || "pasted.txt"}</p>
        ) : (
          <p className="subtitle">Privacy policy overlay</p>
        )}
      </div>
      <div className="header-actions">
        {workspace ? (
          <button className="btn-secondary" type="button" onClick={onLoadPolicy}>
            Load policy
          </button>
        ) : null}
        <button
          className="theme-toggle"
          type="button"
          role="switch"
          aria-checked={theme === "light"}
          aria-label="Toggle light mode"
          onClick={onToggleTheme}
        >
          Dark
          <span className="switch" />
          Light
        </button>
      </div>
    </header>
  );
}
