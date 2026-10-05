"""
Step 2: Preprocess policies - extract privacy content, create policy-level splits
"""
import os
import json
import random
from pathlib import Path
import re
from typing import List, Tuple

# Navigation/boilerplate patterns to skip
NOISE_PATTERNS = [
    r'^\s*-\s*$',
    r'^(about|careers|investors|suppliers|contact|login|logout|menu|search)',
    r'keyboard_arrow',
    r'mark all read',
    r'powered by generative ai',
    r'see all$',
    r'^\s*(all|recalls|unread)\s*$',
    r'notification',
]

# Privacy content indicators
PRIVACY_INDICATORS = [
    'privacy notice',
    'privacy policy',
    'privacy statement',
    'personal information',
    'personal data',
    'data collection',
    'we collect',
    'information we collect',
    'how we use',
    'data retention',
    'your rights',
    'data sharing',
    'third parties',
    'cookies',
    'tracking',
    'security measures',
]

def is_noise_line(line: str) -> bool:
    """Check if line is navigation/boilerplate noise."""
    line_lower = line.lower().strip()
    if len(line_lower) < 3:
        return True
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, line_lower):
            return True
    return False

def detect_privacy_start(lines: List[str]) -> int:
    """Detect where substantive privacy content begins."""
    # Look for strong privacy indicators in headings
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Strong indicators (typically headers)
        if any(indicator in line_lower for indicator in PRIVACY_INDICATORS[:3]):
            # Make sure it's a heading-like line
            if len(line.strip()) < 100 and (line.startswith('#') or line.isupper() or len(line.split()) < 8):
                return max(0, i - 2)  # Include a bit of context before

    # Weaker indicators
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if any(indicator in line_lower for indicator in PRIVACY_INDICATORS[3:]):
            return max(0, i - 5)

    return 0

def extract_privacy_content(content: str) -> str:
    """Extract substantive privacy policy content."""
    lines = content.split('\n')

    # Detect start
    start_idx = detect_privacy_start(lines)

    # Filter noise lines but keep structure
    cleaned_lines = []
    in_privacy_section = False
    noise_streak = 0

    for i, line in enumerate(lines):
        if i < start_idx:
            continue

        if i >= start_idx:
            in_privacy_section = True

        if in_privacy_section:
            if is_noise_line(line):
                noise_streak += 1
                if noise_streak < 3:  # Allow short noise streaks
                    cleaned_lines.append(line)
            else:
                noise_streak = 0
                cleaned_lines.append(line)

    # Remove excessive blank lines
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)

    return result.strip()

def preprocess_corpus(corpus_dir: str, output_dir: str):
    """Preprocess all policies."""
    corpus_path = Path(corpus_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files = sorted(list(corpus_path.glob("*.txt")))
    print(f"Processing {len(files)} files...")

    processed_policies = []

    for file_path in files:
        print(f"  Processing {file_path.name}...")
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        # Extract privacy content
        privacy_content = extract_privacy_content(content)

        # Skip if too short after cleaning
        if len(privacy_content) < 500:
            print(f"    [SKIP] Too short after cleaning: {len(privacy_content)} chars")
            continue

        policy_id = file_path.stem
        output_file = output_path / f"{policy_id}.txt"
        output_file.write_text(privacy_content, encoding='utf-8')

        processed_policies.append({
            "policy_id": policy_id,
            "filename": file_path.name,
            "original_size": len(content),
            "processed_size": len(privacy_content),
            "output_file": str(output_file)
        })

        print(f"    [OK] {len(content):,} -> {len(privacy_content):,} chars")

    print(f"\nProcessed {len(processed_policies)} policies")

    # Save manifest
    manifest_path = output_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(processed_policies, f, indent=2)

    return processed_policies

def create_policy_splits(processed_policies: List[dict], manifests_dir: str, seed: int = 42):
    """Create policy-level train/validation/test splits."""
    random.seed(seed)

    policy_ids = [p['policy_id'] for p in processed_policies]
    random.shuffle(policy_ids)

    n = len(policy_ids)
    train_end = int(0.70 * n)
    val_end = int(0.85 * n)

    train_policies = sorted(policy_ids[:train_end])
    val_policies = sorted(policy_ids[train_end:val_end])
    test_policies = sorted(policy_ids[val_end:])

    print(f"\nPolicy splits:")
    print(f"  Train: {len(train_policies)} policies")
    print(f"  Validation: {len(val_policies)} policies")
    print(f"  Test: {len(test_policies)} policies")

    manifests_path = Path(manifests_dir)
    manifests_path.mkdir(parents=True, exist_ok=True)

    for name, policies in [
        ('train_policies.txt', train_policies),
        ('validation_policies.txt', val_policies),
        ('test_policies.txt', test_policies)
    ]:
        path = manifests_path / name
        path.write_text('\n'.join(policies), encoding='utf-8')

    return train_policies, val_policies, test_policies

if __name__ == "__main__":
    # Preprocess
    policies = preprocess_corpus("../Pdf Trainers", "data/processed")

    # Create splits
    train, val, test = create_policy_splits(policies, "manifests")

    print("\n[COMPLETE] Preprocessing done")
