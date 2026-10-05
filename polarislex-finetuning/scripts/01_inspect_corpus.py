"""
Step 1: Inspect and analyze the privacy policy corpus
"""
import os
import json
from pathlib import Path
from collections import defaultdict
import re

def inspect_corpus(corpus_dir: str):
    """Inspect the privacy policy corpus."""
    corpus_path = Path(corpus_dir)

    files = list(corpus_path.glob("*.txt"))
    print(f"Total files found: {len(files)}")

    stats = {
        "total_files": len(files),
        "file_sizes": [],
        "sample_files": [],
        "total_chars": 0,
        "files_by_size": defaultdict(int)
    }

    for idx, file_path in enumerate(sorted(files)[:10]):
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        size = len(content)
        stats["file_sizes"].append(size)
        stats["total_chars"] += size

        # Detect privacy policy start
        privacy_patterns = [
            r"privacy\s+(notice|policy|statement)",
            r"personal\s+information",
            r"data\s+collection",
            r"we\s+collect"
        ]

        lines = content.split('\n')
        privacy_start = -1
        for i, line in enumerate(lines):
            for pattern in privacy_patterns:
                if re.search(pattern, line.lower()):
                    privacy_start = i
                    break
            if privacy_start >= 0:
                break

        stats["sample_files"].append({
            "name": file_path.name,
            "size": size,
            "lines": len(lines),
            "privacy_starts_at_line": privacy_start
        })

    # Size distribution
    for file_path in files:
        size = len(file_path.read_text(encoding='utf-8', errors='ignore'))
        stats["total_chars"] += size
        if size < 5000:
            stats["files_by_size"]["<5K"] += 1
        elif size < 20000:
            stats["files_by_size"]["5K-20K"] += 1
        elif size < 50000:
            stats["files_by_size"]["20K-50K"] += 1
        elif size < 100000:
            stats["files_by_size"]["50K-100K"] += 1
        else:
            stats["files_by_size"][">100K"] += 1

    avg_size = stats["total_chars"] / len(files) if files else 0
    print(f"\nSize distribution:")
    for size_range, count in sorted(stats["files_by_size"].items()):
        print(f"  {size_range}: {count} files")
    print(f"\nAverage file size: {avg_size:,.0f} characters")

    print(f"\nSample files (first 10):")
    for sample in stats["sample_files"]:
        print(f"  {sample['name']}: {sample['size']:,} chars, {sample['lines']} lines, privacy starts at line {sample['privacy_starts_at_line']}")

    return stats

if __name__ == "__main__":
    corpus_dir = "../Pdf Trainers"
    stats = inspect_corpus(corpus_dir)

    with open("logs/corpus_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
