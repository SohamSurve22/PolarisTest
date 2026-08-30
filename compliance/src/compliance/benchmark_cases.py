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
  "Once provided, consent cannot be withdrawn. By using the Services, you provide broad, continuing and irrevocable consent.",
  "QuickBazaar may deny a request to delete, erase, anonymise, correct, access, retrieve or otherwise manage Personal Data under all circumstances. Personal Data may be retained indefinitely, permanently or for unspecified future purposes.",
  "QuickBazaar does not provide a dedicated privacy grievance officer, Data Protection Officer, complaint portal, telephone line, postal channel, email address or other grievance redressal mechanism.",
  "QuickBazaar may collect, use, disclose, profile, retain and otherwise process Personal Data relating to children without obtaining verifiable consent from a parent or lawful guardian and without applying any additional safeguards.",
  "Notwithstanding anything else in this Privacy Policy, users waive all privacy-related rights, claims, requests and remedies simply by accessing or using the Services.",
  "QuickBazaar may sell, rent, license, exchange, monetise or otherwise commercially exploit Personal Data.",
  "QuickBazaar may transfer Personal Data to any country without regard to restrictions, prohibitions, conditions or requirements imposed under Applicable Indian Law.",
  "QuickBazaar accepts no responsibility or liability for any security incident, data breach, unauthorised access, loss, disclosure or misuse caused by the acts or omissions of its employees, agents, contractors or service providers.",
]
PARTIAL_TEXTS = [
  "We obtain consent for some processing activities.",
  "We handle security incidents according to applicable legal requirements and timelines.",
  "We may retain data as needed.",
]
AMBIGUOUS_TEXTS = ["We comply with all applicable laws and applicable legal requirements."]
