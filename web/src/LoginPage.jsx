import { useState } from "react";
import "./LoginPage.css";
import { isGovtEmail, saveSession } from "./auth.js";

const ROLES = {
  user: {
    label: "Citizen / User",
    blurb: "Check a privacy policy against Indian data-protection law.",
  },
  officer: {
    label: "Government Officer",
    blurb: "Review compliance reports and oversee policy analysis.",
  },
};

async function post(path, body) {
  const response = await fetch(`/api/auth/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong");
  }
  return data;
}

export default function LoginPage({ onSuccess, onBack }) {
  const [role, setRole] = useState("user");
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const canRegister = role === "user"; // officer accounts are issued by an admin
  const registering = mode === "register" && canRegister;

  function pickRole(next) {
    setRole(next);
    setMode("login");
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (role === "officer" && !isGovtEmail(email)) {
      setError("Officers must sign in with an official government email (gov.in or nic.in).");
      return;
    }
    setBusy(true);
    try {
      if (registering) {
        await post("register", { email, password, role: "user" });
      }
      const data = await post("login", { email, password, role });
      saveSession({ token: data.token, role: data.role, email });
      onSuccess(data.role);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="lg-page">
      <header className="lg-nav">
        <div className="lg-nav-inner">
          <button type="button" className="lg-logo" onClick={onBack} aria-label="Back to home">
            <span className="lg-logo-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="6" r="2.2" />
                <circle cx="6" cy="17" r="2.2" />
                <circle cx="18" cy="17" r="2.2" />
                <path d="M12 8.2 7 15M12 8.2l5 6.8M8.2 17h7.6" />
              </svg>
            </span>
            <span className="lg-logo-text">PolarisLex</span>
            <span className="lg-pill">Compliance Graph</span>
          </button>
          <button type="button" className="lg-back" onClick={onBack}>
            ← Back to home
          </button>
        </div>
      </header>

      <main className="lg-main">
        <div className="lg-badge">
          <span className="lg-dot" /> Secure access
        </div>
        <h1 className="lg-title">
          Sign in to <span className="lg-grad">PolarisLex</span>
        </h1>
        <p className="lg-sub">Choose how you want to continue.</p>

        <div className="lg-card">
          <div className="lg-roles" role="tablist" aria-label="Login as">
            {Object.entries(ROLES).map(([key, item]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={role === key}
                className={`lg-role ${role === key ? "is-active" : ""}`}
                onClick={() => pickRole(key)}
              >
                <span className="lg-role-title">{item.label}</span>
                <span className="lg-role-blurb">{item.blurb}</span>
              </button>
            ))}
          </div>

          <form className="lg-form" onSubmit={submit}>
            <label htmlFor="lg-email">Email</label>
            <input
              id="lg-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={role === "officer" ? "officer@gov.in" : "you@example.com"}
            />

            {role === "officer" ? (
              <p className="lg-hint">Use your official government email (gov.in or nic.in).</p>
            ) : null}

            <label htmlFor="lg-password">Password</label>
            <input
              id="lg-password"
              type="password"
              required
              minLength={6}
              autoComplete={registering ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
            />

            {error ? (
              <p className="lg-error" role="alert">
                {error}
              </p>
            ) : null}

            <button type="submit" className="lg-submit" disabled={busy}>
              {busy
                ? "Please wait…"
                : registering
                  ? "Create account"
                  : `Sign in as ${ROLES[role].label}`}
            </button>
          </form>

          {canRegister ? (
            <p className="lg-switch">
              {registering ? "Already have an account?" : "New here?"}{" "}
              <button
                type="button"
                onClick={() => {
                  setMode(registering ? "login" : "register");
                  setError("");
                }}
              >
                {registering ? "Sign in" : "Create an account"}
              </button>
            </p>
          ) : (
            <p className="lg-switch">Officer accounts are issued by your department administrator.</p>
          )}
        </div>

        <ul className="lg-trust">
          <li>DPDP Act 2023 Ready</li>
          <li>GraphRAG Traversal</li>
          <li>Explainable Audit Trail</li>
        </ul>
      </main>
    </div>
  );
}
