"""
Step 4: Fine-tune Qwen2.5-3B-Instruct using Unsloth/QLoRA
Optimized for GTX 1660 Ti (6GB VRAM)
"""
import torch
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import json
from pathlib import Path

# Check CUDA availability
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA version: {torch.version.cuda}")

# Model configuration
MODEL_NAME = "unsloth/Qwen2.5-3B-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 2048  # Reduced for 6GB VRAM
DTYPE = None  # Auto-detect

# LoRA configuration (conservative for 6GB VRAM)
LORA_R = 16
LORA_ALPHA = 16
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

def load_model_and_tokenizer():
    """Load 4-bit quantized model with LoRA adapters."""
    print("\n=== Loading Model ===")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=DTYPE,
        load_in_4bit=True,
    )

    # Add LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=TARGET_MODULES,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    print(f"Model loaded: {MODEL_NAME}")
    print(f"LoRA rank: {LORA_R}, alpha: {LORA_ALPHA}")

    return model, tokenizer

def format_prompt(instruction: str, input_text: str, output: str = None) -> str:
    """Format prompt using Qwen chat template."""
    if output is None:
        # Inference mode
        prompt = f"<|im_start|>system\nYou are an expert privacy policy analyst. Extract information accurately and provide evidence from the text.<|im_end|>\n<|im_start|>user\n{instruction}\n\nText:\n{input_text}<|im_end|>\n<|im_start|>assistant\n"
    else:
        # Training mode
        prompt = f"<|im_start|>system\nYou are an expert privacy policy analyst. Extract information accurately and provide evidence from the text.<|im_end|>\n<|im_start|>user\n{instruction}\n\nText:\n{input_text}<|im_end|>\n<|im_start|>assistant\n{output}<|im_end|>"

    return prompt

def formatting_prompts_func(examples):
    """Format examples for training."""
    instructions = examples["instruction"]
    inputs = examples["input"]
    outputs = examples["output"]

    texts = []
    for instruction, input_text, output in zip(instructions, inputs, outputs):
        text = format_prompt(instruction, input_text, output)
        texts.append(text)

    return {"text": texts}

def load_datasets():
    """Load training, validation, and test datasets."""
    print("\n=== Loading Datasets ===")

    train_dataset = load_dataset("json", data_files="data/train.jsonl", split="train")
    val_dataset = load_dataset("json", data_files="data/validation.jsonl", split="train")
    test_dataset = load_dataset("json", data_files="data/test.jsonl", split="train")

    print(f"Training examples: {len(train_dataset)}")
    print(f"Validation examples: {len(val_dataset)}")
    print(f"Test examples: {len(test_dataset)}")

    # Format datasets
    train_dataset = train_dataset.map(formatting_prompts_func, batched=True)
    val_dataset = val_dataset.map(formatting_prompts_func, batched=True)

    return train_dataset, val_dataset, test_dataset

def train_model(model, tokenizer, train_dataset, val_dataset):
    """Train the model using SFTTrainer."""
    print("\n=== Training Configuration ===")

    # Training arguments optimized for 6GB VRAM
    training_args = TrainingArguments(
        output_dir="adapters/polarislex-qwen2.5-3b",
        per_device_train_batch_size=1,  # Minimum for 6GB
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,  # Effective batch size = 8
        warmup_steps=50,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        evaluation_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
        optim="adamw_8bit",  # 8-bit optimizer to save memory
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",  # Disable wandb
    )

    print(f"Batch size: {training_args.per_device_train_batch_size}")
    print(f"Gradient accumulation: {training_args.gradient_accumulation_steps}")
    print(f"Effective batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
    print(f"Learning rate: {training_args.learning_rate}")
    print(f"Epochs: {training_args.num_train_epochs}")
    print(f"FP16: {training_args.fp16}, BF16: {training_args.bf16}")

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=training_args,
        packing=False,  # Don't pack sequences for privacy policy data
    )

    print("\n=== Starting Training ===")

    # Train
    trainer.train()

    print("\n=== Training Complete ===")

    # Save final model
    model.save_pretrained("adapters/polarislex-qwen2.5-3b/final")
    tokenizer.save_pretrained("adapters/polarislex-qwen2.5-3b/final")

    print(f"Model saved to: adapters/polarislex-qwen2.5-3b/final")

    return trainer

def smoke_test(model, tokenizer):
    """Quick smoke test before full training."""
    print("\n=== SMOKE TEST ===")

    # Load a few examples
    test_data = load_dataset("json", data_files="data/train.jsonl", split="train[:5]")
    test_data = test_data.map(formatting_prompts_func, batched=True)

    # Quick training args
    smoke_args = TrainingArguments(
        output_dir="adapters/smoke_test",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=2,
        max_steps=3,  # Just 3 steps
        logging_steps=1,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        optim="adamw_8bit",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=test_data,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=smoke_args,
        packing=False,
    )

    print("Running smoke test (3 steps)...")
    trainer.train()

    print("✓ Smoke test passed!")
    print("  - Model loads successfully")
    print("  - CUDA works")
    print("  - Forward pass works")
    print("  - Backward pass works")
    print("  - Training progresses")

    return True

def main():
    # Load model and tokenizer
    model, tokenizer = load_model_and_tokenizer()

    # Load datasets
    train_dataset, val_dataset, test_dataset = load_datasets()

    # Run smoke test
    print("\n" + "="*60)
    print("SMOKE TEST - Verifying setup before full training")
    print("="*60)

    smoke_test(model, tokenizer)

    # Reload model for actual training (smoke test modified it)
    print("\nReloading model for full training...")
    model, tokenizer = load_model_and_tokenizer()

    # Full training
    print("\n" + "="*60)
    print("FULL TRAINING")
    print("="*60)

    trainer = train_model(model, tokenizer, train_dataset, val_dataset)

    # Log training stats
    stats = {
        "total_examples": len(train_dataset),
        "validation_examples": len(val_dataset),
        "test_examples": len(test_dataset),
        "epochs": trainer.args.num_train_epochs,
        "final_loss": trainer.state.log_history[-1].get("loss", None) if trainer.state.log_history else None,
        "model_path": "adapters/polarislex-qwen2.5-3b/final"
    }

    with open("logs/training_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n{'='*60}")
    print("TRAINING COMPLETE!")
    print(f"{'='*60}")
    print(f"Final model saved to: {stats['model_path']}")
    print(f"Training stats saved to: logs/training_stats.json")

if __name__ == "__main__":
    main()
