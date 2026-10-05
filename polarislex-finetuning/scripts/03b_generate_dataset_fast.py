"""
Fast dataset generation using rule-based extraction + validation
This approach is faster and more reliable than pure LLM generation
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import random
from collections import defaultdict

# Privacy provision types
PROVISION_TYPES = [
    "personal_data_collection",
    "data_use_processing",
    "purpose_of_processing",
    "sharing_disclosure",
    "retention",
    "security",
    "user_rights",
    "consent",
    "children_privacy",
    "cookies_tracking",
    "data_deletion",
    "data_access",
    "international_transfer",
    "grievance_contact",
    "other"
]

# Data entity patterns
DATA_ENTITY_PATTERNS = [
    r'(?:collect|process|use|share|disclose|store|retain)\s+(?:your\s+)?([a-z\s]+(?:information|data|address|name|number|id|identifier))',
    r'personal\s+(information|data)',
    r'(email\s+address)',
    r'(phone\s+number)',
    r'(IP\s+address)',
    r'(cookies?)',
    r'(location\s+data)',
    r'(device\s+information)',
    r'(payment\s+information)',
    r'(biometric\s+data)',
    r'(health\s+information)',
    r'(financial\s+information)',
]

def chunk_policy(content: str, max_chunk_size: int = 600) -> List[str]:
    """Chunk policy into manageable segments."""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        if current_size + para_size > max_chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks

def classify_provision(text: str) -> str:
    """Rule-based provision classification."""
    text_lower = text.lower()

    # Classification rules
    if any(word in text_lower for word in ['collect', 'obtain', 'receive', 'gather']):
        if any(word in text_lower for word in ['personal', 'information', 'data']):
            return "personal_data_collection"

    if any(word in text_lower for word in ['share', 'disclose', 'third party', 'third-party']):
        return "sharing_disclosure"

    if any(word in text_lower for word in ['retain', 'retention', 'keep', 'store']):
        return "retention"

    if any(word in text_lower for word in ['security', 'protect', 'safeguard', 'secure']):
        return "security"

    if any(word in text_lower for word in ['right', 'access', 'delete', 'correct', 'opt-out']):
        return "user_rights"

    if any(word in text_lower for word in ['consent', 'permission', 'agree']):
        return "consent"

    if any(word in text_lower for word in ['child', 'children', 'under 13', 'under 16']):
        return "children_privacy"

    if any(word in text_lower for word in ['cookie', 'tracking', 'analytics', 'pixel']):
        return "cookies_tracking"

    if any(word in text_lower for word in ['delete', 'deletion', 'remove', 'erase']):
        return "data_deletion"

    if any(word in text_lower for word in ['access', 'view', 'download', 'copy']):
        return "data_access"

    if any(word in text_lower for word in ['international', 'transfer', 'cross-border']):
        return "international_transfer"

    if any(word in text_lower for word in ['contact', 'grievance', 'complaint', 'officer']):
        return "grievance_contact"

    if any(word in text_lower for word in ['use', 'process', 'purpose']):
        return "data_use_processing"

    return "other"

def extract_data_entities(text: str) -> List[Dict]:
    """Extract data entities using patterns."""
    entities = []
    seen = set()

    for pattern in DATA_ENTITY_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            entity_text = match.group(0)
            if len(entity_text) < 10:  # Skip very short matches
                continue

            # Extract the entity name
            entity_name = match.group(1) if match.groups() else entity_text
            entity_name = entity_name.strip().lower()

            if entity_name in seen:
                continue
            seen.add(entity_name)

            # Extract context (surrounding sentence)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].strip()

            # Find sentence boundaries
            sentences = re.split(r'[.!?]\s+', context)
            evidence = ""
            for sent in sentences:
                if entity_text.lower() in sent.lower():
                    evidence = sent.strip()
                    break

            if not evidence:
                evidence = context[:200]

            # Validate evidence is in original text
            if evidence not in text:
                continue

            entities.append({
                "item": entity_name,
                "evidence": evidence,
                "action": "",
                "purpose": ""
            })

            if len(entities) >= 5:  # Limit per chunk
                break

    return entities

def generate_classification_example(chunk: str, policy_id: str) -> Optional[Dict]:
    """Generate classification training example."""
    if len(chunk.split()) < 15:
        return None

    provision_type = classify_provision(chunk)

    return {
        "instruction": f"Classify this privacy policy provision into one of these categories: {', '.join(PROVISION_TYPES)}",
        "input": chunk,
        "output": json.dumps({"provision_type": provision_type}),
        "task_type": "classification",
        "policy_id": policy_id
    }

def generate_entity_extraction_example(chunk: str, policy_id: str) -> Optional[Dict]:
    """Generate entity extraction training example."""
    if len(chunk.split()) < 15:
        return None

    entities = extract_data_entities(chunk)

    if not entities:
        return None

    return {
        "instruction": "Extract personal data entities, their collection/use actions, and purposes from this privacy policy text. For each entity, provide exact evidence from the text.",
        "input": chunk,
        "output": json.dumps({"data_entities": entities}),
        "task_type": "entity_extraction",
        "policy_id": policy_id
    }

def validate_example(example: Dict) -> bool:
    """Validate a generated example."""
    if not all(k in example for k in ['instruction', 'input', 'output', 'task_type']):
        return False

    if not example['instruction'] or not example['input'] or not example['output']:
        return False

    # Validate JSON in output
    try:
        output_data = json.loads(example['output'])
    except:
        return False

    # Task-specific validation
    if example['task_type'] == 'classification':
        if 'provision_type' not in output_data:
            return False
        if output_data['provision_type'] not in PROVISION_TYPES:
            return False

    elif example['task_type'] == 'entity_extraction':
        if 'data_entities' not in output_data:
            return False

        # Validate evidence grounding
        for entity in output_data.get('data_entities', []):
            if 'evidence' in entity and entity['evidence']:
                # STRICT: Evidence must appear in input
                if entity['evidence'] not in example['input']:
                    return False

    return True

def generate_examples_from_policy(policy_path: Path, policy_id: str, max_examples: int = 15) -> List[Dict]:
    """Generate training examples from a single policy."""
    print(f"  Generating from {policy_id}...")

    content = policy_path.read_text(encoding='utf-8')
    chunks = chunk_policy(content, max_chunk_size=500)

    # Sample chunks if too many
    if len(chunks) > max_examples:
        chunks = random.sample(chunks, max_examples)

    examples = []
    rejected = defaultdict(int)

    for chunk_idx, chunk in enumerate(chunks):
        if len(chunk.split()) < 20:
            continue

        # Generate both types of examples
        for gen_func, task_name in [
            (generate_classification_example, 'classification'),
            (generate_entity_extraction_example, 'entity_extraction')
        ]:
            ex = gen_func(chunk, policy_id)
            if ex:
                if validate_example(ex):
                    ex['chunk_idx'] = chunk_idx
                    examples.append(ex)
                else:
                    rejected[f'invalid_{task_name}'] += 1
            else:
                rejected[f'failed_{task_name}'] += 1

    print(f"    Generated: {len(examples)}, Rejected: {dict(rejected)}")
    return examples

def generate_dataset_split(policy_ids: List[str], processed_dir: str, max_per_policy: int = 15) -> List[Dict]:
    """Generate dataset for a policy split."""
    processed_path = Path(processed_dir)
    all_examples = []

    for policy_id in policy_ids:
        policy_path = processed_path / f"{policy_id}.txt"
        if not policy_path.exists():
            print(f"  [SKIP] Policy file not found: {policy_id}")
            continue

        examples = generate_examples_from_policy(policy_path, policy_id, max_examples=max_per_policy)
        all_examples.extend(examples)

    return all_examples

def save_dataset(examples: List[Dict], output_path: str):
    """Save dataset in JSONL format."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for ex in examples:
            # Keep only required fields for training
            train_ex = {
                'instruction': ex['instruction'],
                'input': ex['input'],
                'output': ex['output']
            }
            f.write(json.dumps(train_ex, ensure_ascii=False) + '\n')

    print(f"Saved {len(examples)} examples to {output_path}")

if __name__ == "__main__":
    random.seed(42)

    # Load policy splits
    train_policies = Path("manifests/train_policies.txt").read_text().strip().split('\n')
    val_policies = Path("manifests/validation_policies.txt").read_text().strip().split('\n')
    test_policies = Path("manifests/test_policies.txt").read_text().strip().split('\n')

    print(f"Loaded splits: {len(train_policies)} train, {len(val_policies)} val, {len(test_policies)} test")

    # Generate training set
    print("\n=== GENERATING TRAINING SET ===")
    train_examples = generate_dataset_split(train_policies[:40], "data/processed", max_per_policy=8)
    save_dataset(train_examples, "data/train.jsonl")

    # Generate validation set
    print("\n=== GENERATING VALIDATION SET ===")
    val_examples = generate_dataset_split(val_policies[:10], "data/processed", max_per_policy=4)
    save_dataset(val_examples, "data/validation.jsonl")

    # Generate test set
    print("\n=== GENERATING TEST SET ===")
    test_examples = generate_dataset_split(test_policies[:10], "data/processed", max_per_policy=4)
    save_dataset(test_examples, "data/test.jsonl")

    # Statistics
    print("\n=== DATASET STATISTICS ===")
    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(val_examples)}")
    print(f"Test examples: {len(test_examples)}")

    # Task distribution
    train_tasks = defaultdict(int)
    for ex in train_examples:
        train_tasks[ex['task_type']] += 1
    print(f"\nTraining task distribution: {dict(train_tasks)}")

    # Provision distribution for classification tasks
    provision_dist = defaultdict(int)
    for ex in train_examples:
        if ex['task_type'] == 'classification':
            output_data = json.loads(ex['output'])
            provision_dist[output_data['provision_type']] += 1
    print(f"\nProvision type distribution:")
    for prov_type, count in sorted(provision_dist.items(), key=lambda x: -x[1]):
        print(f"  {prov_type}: {count}")
