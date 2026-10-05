"""
Step 3: Generate supervised fine-tuning dataset from privacy policies
Uses local Qwen to generate candidate examples, then validates them rigorously
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import random
from collections import defaultdict
import ollama

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

def chunk_policy(content: str, max_chunk_size: int = 800) -> List[str]:
    """Chunk policy into manageable segments for processing."""
    # Split by double newline (paragraphs)
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

def generate_classification_example(chunk: str, model: str = "qwen2.5:7b-instruct-q4_K_M") -> Optional[Dict]:
    """Generate provision classification example."""
    prompt = f"""Classify the following privacy policy text into ONE of these categories: {', '.join(PROVISION_TYPES)}

Text:
{chunk}

Respond with ONLY a JSON object in this format:
{{"provision_type": "category_name"}}

If the text doesn't clearly fit any category or contains multiple unrelated provisions, respond with {{"provision_type": "other"}}"""

    try:
        response = ollama.generate(model=model, prompt=prompt, options={"temperature": 0.1})
        output = response['response'].strip()

        # Extract JSON
        json_match = re.search(r'\{[^}]+\}', output)
        if not json_match:
            return None

        result = json.loads(json_match.group(0))

        # Validate
        if 'provision_type' not in result:
            return None
        if result['provision_type'] not in PROVISION_TYPES:
            return None

        return {
            "instruction": f"Classify this privacy policy provision into one of these categories: {', '.join(PROVISION_TYPES)}",
            "input": chunk,
            "output": json.dumps(result),
            "task_type": "classification"
        }
    except Exception as e:
        print(f"    [ERROR] Classification generation failed: {e}")
        return None

def generate_entity_extraction_example(chunk: str, model: str = "qwen2.5:7b-instruct-q4_K_M") -> Optional[Dict]:
    """Generate entity extraction example."""
    prompt = f"""Extract personal data entities mentioned in this privacy policy text.

Text:
{chunk}

For each data entity found, provide:
1. The specific data item
2. The exact quote from the text as evidence
3. Any action mentioned (collection, use, sharing, etc.)
4. Any stated purpose

Respond with ONLY a JSON object in this format:
{{
  "data_entities": [
    {{
      "item": "specific data type",
      "evidence": "exact quote from text",
      "action": "collection/use/sharing/etc or empty string",
      "purpose": "stated purpose or empty string"
    }}
  ]
}}

CRITICAL: The evidence field MUST be an exact substring from the input text. Do not paraphrase."""

    try:
        response = ollama.generate(model=model, prompt=prompt, options={"temperature": 0.1})
        output = response['response'].strip()

        # Extract JSON
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if not json_match:
            return None

        result = json.loads(json_match.group(0))

        # Validate structure
        if 'data_entities' not in result:
            return None
        if not isinstance(result['data_entities'], list):
            return None
        if len(result['data_entities']) == 0:
            return None

        # Validate each entity
        for entity in result['data_entities']:
            if 'item' not in entity or 'evidence' not in entity:
                return None

            # CRITICAL: Validate evidence is in source
            if entity['evidence'] not in chunk:
                # Try case-insensitive match
                if entity['evidence'].lower() not in chunk.lower():
                    print(f"    [REJECT] Evidence not found in source: {entity['evidence'][:50]}...")
                    return None

        return {
            "instruction": "Extract personal data entities, their collection/use actions, and purposes from this privacy policy text. For each entity, provide exact evidence from the text.",
            "input": chunk,
            "output": json.dumps(result),
            "task_type": "entity_extraction"
        }
    except Exception as e:
        print(f"    [ERROR] Entity extraction failed: {e}")
        return None

def validate_example(example: Dict) -> bool:
    """Validate a generated example."""
    # Check required fields
    if not all(k in example for k in ['instruction', 'input', 'output', 'task_type']):
        return False

    # Check non-empty
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
            if 'evidence' in entity:
                evidence = entity['evidence']
                # STRICT: Evidence must appear in input
                if evidence not in example['input']:
                    # Try case-insensitive
                    if evidence.lower() not in example['input'].lower():
                        return False

    return True

def generate_examples_from_policy(policy_path: Path, policy_id: str, max_examples: int = 20) -> List[Dict]:
    """Generate training examples from a single policy."""
    print(f"  Generating from {policy_id}...")

    content = policy_path.read_text(encoding='utf-8')
    chunks = chunk_policy(content, max_chunk_size=600)

    # Sample chunks if too many
    if len(chunks) > max_examples:
        chunks = random.sample(chunks, max_examples)

    examples = []
    rejected = defaultdict(int)

    for chunk_idx, chunk in enumerate(chunks):
        if len(chunk.split()) < 20:  # Skip tiny chunks
            continue

        # Generate classification example
        if random.random() < 0.5:  # 50% classification
            ex = generate_classification_example(chunk)
            if ex:
                if validate_example(ex):
                    ex['policy_id'] = policy_id
                    ex['chunk_idx'] = chunk_idx
                    examples.append(ex)
                else:
                    rejected['invalid_classification'] += 1
            else:
                rejected['failed_classification'] += 1

        # Generate entity extraction example
        else:  # 50% entity extraction
            ex = generate_entity_extraction_example(chunk)
            if ex:
                if validate_example(ex):
                    ex['policy_id'] = policy_id
                    ex['chunk_idx'] = chunk_idx
                    examples.append(ex)
                else:
                    rejected['invalid_entity_extraction'] += 1
            else:
                rejected['failed_entity_extraction'] += 1

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
    # Load policy splits
    train_policies = Path("manifests/train_policies.txt").read_text().strip().split('\n')
    val_policies = Path("manifests/validation_policies.txt").read_text().strip().split('\n')
    test_policies = Path("manifests/test_policies.txt").read_text().strip().split('\n')

    print(f"Loaded splits: {len(train_policies)} train, {len(val_policies)} val, {len(test_policies)} test")

    # Generate training set (smaller sample for faster development)
    print("\n=== GENERATING TRAINING SET (SAMPLE) ===")
    train_sample = train_policies[:20]  # Use 20 policies for training
    train_examples = generate_dataset_split(train_sample, "data/processed", max_per_policy=8)
    save_dataset(train_examples, "data/train.jsonl")

    # Generate validation set
    print("\n=== GENERATING VALIDATION SET ===")
    val_examples = generate_dataset_split(val_policies[:5], "data/processed", max_per_policy=4)
    save_dataset(val_examples, "data/validation.jsonl")

    # Generate test set
    print("\n=== GENERATING TEST SET ===")
    test_examples = generate_dataset_split(test_policies[:5], "data/processed", max_per_policy=4)
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
