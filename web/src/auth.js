// Session helpers for the login token kept in sessionStorage.
const KEY = "polaris-auth";

// Official government email domains (kept in sync with auth.py).
const GOVT_DOMAINS = ["gov.in", "nic.in"];

export function isGovtEmail(email) {
  const domain = String(email).trim().toLowerCase().split("@")[1] || "";
  return GOVT_DOMAINS.some((d) => domain === d || domain.endsWith(`.${d}`));
}

function tokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return !payload.exp || payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

// Returns { token, role, email } or null if not logged in / token expired.
export function getSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(KEY) || "null");
    if (!session || !session.token || tokenExpired(session.token)) {
      sessionStorage.removeItem(KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function saveSession(session) {
  sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession() {
  sessionStorage.removeItem(KEY);
}
