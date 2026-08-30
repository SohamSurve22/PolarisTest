"""Shared clause fixtures for frozen engine benchmarks."""

PASS_TEXTS = [
  "We obtain informed consent before processing personal data for specified purposes. You may withdraw consent and we will stop processing.",
  "We provide notice in plain language and a privacy notice describing purposes.",
  "BharatPay implements encryption, tokenisation, MFA, least-privilege access, logging, monitoring, backups and vendor due diligence.",
  "We notify the Board and affected data principals of a personal data breach.",
  "We delete personal data when the purpose ends and do not retain it longer than needed.",
  "A grievance officer is available at privacy@bharatpay.example.in.",
  "We do not process children's data without parental consent and we do not track children for advertising.",
  "Cross-border transfers follow applicable transfer conditions outside India.",
  "Processors are bound by written contracts.",
  "We keep personal data accurate and up to date.",
  "This privacy policy is published and available on our website.",
  "We share data with third parties only with prior consent.",
  "Security incidents are reported to CERT-In including malware and unauthorised access.",
  "We take reasonable security practices to protect sensitive personal data.",
]
FAIL_TEXTS = [
  "We do not encrypt personal data and we do not implement security safeguards.",
  "We do not notify anyone of a breach. We will not report a breach.",
  "We track children for targeted advertising.",
]
PARTIAL_TEXTS = [
  "We obtain consent for some processing activities.",
  "We handle security incidents according to applicable legal requirements and timelines.",
  "We may retain data as needed.",
]
AMBIGUOUS_TEXTS = ["We comply with all applicable laws and applicable legal requirements."]
