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
    "cyber", "information security", "incident",
  ),
  "TOPIC_CYBER_SECURITY": (
    "cyber", "information security",
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


def topic_title(topic_id: str) -> str:
  """Human label for a TOPIC_* id."""
  return topic_id.removeprefix("TOPIC_").replace("_", " ").title()
