"""Kept website-privacy topics and display titles."""

from __future__ import annotations

KEPT_TOPICS: frozenset[str] = frozenset({
  "TOPIC_CONSENT",
  "TOPIC_DATA_PROCESSING",
  "TOPIC_USER_RIGHTS",
  "TOPIC_CHILDREN_DATA",
  "TOPIC_SECURITY",
  "TOPIC_DATA_RETENTION",
  "TOPIC_BREACH_REPORTING",
  "TOPIC_GRIEVANCE_REDRESSAL",
  "TOPIC_CROSS_BORDER_TRANSFER",
  "TOPIC_SENSITIVE_PERSONAL_DATA",
  "TOPIC_COLLECTION_OF_INFORMATION",
  "TOPIC_DISCLOSURE",
  "TOPIC_LAWFUL_PROCESSING",
  "TOPIC_PRIVACY_POLICY",
  "TOPIC_CORRECTION",
  "TOPIC_WITHDRAWAL_OF_CONSENT",
  "TOPIC_INCIDENT_REPORTING",
  "TOPIC_RECORD_RETENTION",
  "TOPIC_LOG_RETENTION",
  "TOPIC_CYBERSECURITY",
  "TOPIC_CYBER_SECURITY",
  "TOPIC_REGULATORY_REPORTING",
  "TOPIC_AUDIT",
  "TOPIC_ISO_27001",
})

KEEP_CHUNK_TYPES: frozenset[str] = frozenset({
  "obligation",
  "right",
  "compliance_requirement",
  "restriction",
})

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
  "TOPIC_CONSENT": (
    "consent", "opt-in", "opt in", "withdraw", "cookie", "agree",
  ),
  "TOPIC_DATA_PROCESSING": (
    "process", "processing", "use your", "how we use", "personal data",
  ),
  "TOPIC_USER_RIGHTS": (
    "your rights", "access", "delete", "erasure", "portability", "rectif",
  ),
  "TOPIC_CHILDREN_DATA": (
    "child", "children", "under 18", "under 13", "minor",
  ),
  "TOPIC_SECURITY": (
    "security", "safeguard", "encrypt", "protect your",
  ),
  "TOPIC_DATA_RETENTION": (
    "retain", "retention", "how long", "keep your", "storage period",
  ),
  "TOPIC_BREACH_REPORTING": (
    "breach", "incident", "notify", "data leak",
  ),
  "TOPIC_GRIEVANCE_REDRESSAL": (
    "grievance", "complaint", "contact us", "dpo", "officer",
  ),
  "TOPIC_CROSS_BORDER_TRANSFER": (
    "transfer", "outside india", "cross-border", "international",
  ),
  "TOPIC_SENSITIVE_PERSONAL_DATA": (
    "sensitive", "biometric", "health", "financial information",
  ),
  "TOPIC_COLLECTION_OF_INFORMATION": (
    "collect", "information we collect", "what we collect",
  ),
  "TOPIC_DISCLOSURE": (
    "share", "disclosure", "third part", "recipients",
  ),
  "TOPIC_LAWFUL_PROCESSING": (
    "lawful", "legal basis", "legitimate",
  ),
  "TOPIC_PRIVACY_POLICY": (
    "privacy policy", "this policy",
  ),
  "TOPIC_CORRECTION": (
    "correct", "update your", "rectif",
  ),
  "TOPIC_WITHDRAWAL_OF_CONSENT": (
    "withdraw consent", "opt out", "unsubscribe",
  ),
  "TOPIC_INCIDENT_REPORTING": (
    "cyber incident", "report incident", "cert-in", "certin",
  ),
  "TOPIC_RECORD_RETENTION": (
    "logs", "log retention", "180 days", "records",
  ),
  "TOPIC_LOG_RETENTION": (
    "logs", "log retention", "180 days",
  ),
  "TOPIC_CYBERSECURITY": (
    "cyber", "cybersecurity", "information security", "incident",
    "security", "safeguard", "encrypt",
  ),
  "TOPIC_CYBER_SECURITY": (
    "cyber", "cybersecurity", "information security",
    "security", "safeguard", "encrypt",
  ),
  "TOPIC_REGULATORY_REPORTING": (
    "report", "regulator", "cert-in",
  ),
  "TOPIC_AUDIT": (
    "audit", "iso",
  ),
  "TOPIC_ISO_27001": (
    "iso 27001", "iso27001",
  ),
}


TOPIC_THEME: dict[str, str] = {
  "TOPIC_PRIVACY_POLICY": "notice",
  "TOPIC_LAWFUL_PROCESSING": "notice",
  "TOPIC_COLLECTION_OF_INFORMATION": "collection",
  "TOPIC_SENSITIVE_PERSONAL_DATA": "collection",
  "TOPIC_DISCLOSURE": "collection",
  "TOPIC_DATA_PROCESSING": "collection",
  "TOPIC_CONSENT": "consent",
  "TOPIC_WITHDRAWAL_OF_CONSENT": "consent",
  "TOPIC_USER_RIGHTS": "rights",
  "TOPIC_CORRECTION": "rights",
  "TOPIC_CHILDREN_DATA": "rights",
  "TOPIC_GRIEVANCE_REDRESSAL": "rights",
  "TOPIC_DATA_RETENTION": "retention",
  "TOPIC_RECORD_RETENTION": "retention",
  "TOPIC_LOG_RETENTION": "retention",
  "TOPIC_SECURITY": "security",
  "TOPIC_CYBERSECURITY": "security",
  "TOPIC_CYBER_SECURITY": "security",
  "TOPIC_AUDIT": "security",
  "TOPIC_ISO_27001": "security",
  "TOPIC_CROSS_BORDER_TRANSFER": "transfers",
  "TOPIC_BREACH_REPORTING": "incidents",
  "TOPIC_INCIDENT_REPORTING": "incidents",
  "TOPIC_REGULATORY_REPORTING": "incidents",
}

_STATUTE_TITLES: dict[str, str] = {
  "DPDP": "DPDP",
  "SPDI_RULES_2011": "SPDI",
  "SPDI": "SPDI",
  "CERTIN_DIRECTIONS_2022": "CERT-In",
  "CERTIN": "CERT-In",
  "IT_ACT_2000": "IT Act",
  "TINY": "Tiny",
}


def topic_title(topic_id: str) -> str:
  """Human label for a TOPIC_* id (strips @act suffix)."""
  base = base_topic_id(topic_id)
  return base.removeprefix("TOPIC_").replace("_", " ").title()


def base_topic_id(topic_id: str) -> str:
  """TOPIC_CONSENT@DPDP → TOPIC_CONSENT."""
  return topic_id.split("@", 1)[0]


def theme_for_topic(topic_id: str) -> str:
  """Theme bucket id for a kept topic."""
  return TOPIC_THEME.get(base_topic_id(topic_id), "other")


def theme_title(theme_id: str) -> str:
  """Human label for a theme bucket."""
  return theme_id.replace("_", " ").title()


def statute_key(act: str) -> str:
  """Stable cluster id fragment for a statute act string."""
  cleaned = (act or "").strip() or "OTHER"
  return cleaned


def statute_title(act: str) -> str:
  """Display name for a statute cluster."""
  key = statute_key(act)
  if key in _STATUTE_TITLES:
    return _STATUTE_TITLES[key]
  return key.replace("_", " ").title()
