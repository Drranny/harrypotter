"""
Audit text-track dataset quality.

Checks:
- raw file inventory and empty file detection
- page header/footer noise count (`Page | N`)
- repeated blank-line density
- eval JSONL validity and gold_sources coverage

Usage:
    python3 scripts/audit_text_data.py
"""

import json
import os
import re
from typing import Dict, List

RAW_DIR = "data/text/raw"
EVAL_PATH = "data/text/eval/queries_text_main.jsonl"


def list_text_files(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    return sorted(
        [
            os.path.join(path, name)
            for name in os.listdir(path)
            if os.path.isfile(os.path.join(path, name)) and name.lower().endswith(".txt")
        ]
    )


def analyze_text_file(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    page_markers = len(re.findall(r"Page\s*\|\s*\d+", text, flags=re.IGNORECASE))
    repeated_blank_runs = len(re.findall(r"\n\s*\n\s*\n+", text))
    chars = len(text)

    return {
        "file": os.path.basename(path),
        "chars": chars,
        "page_markers": page_markers,
        "repeated_blank_runs": repeated_blank_runs,
        "empty": chars == 0,
    }


def load_eval(path: str) -> List[Dict]:
    rows: List[Dict] = []
    if not os.path.exists(path):
        return rows

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                rows.append({"_error": f"line {idx}: {e}"})
                continue
            rows.append(row)
    return rows


def main() -> int:
    files = list_text_files(RAW_DIR)
    print("=" * 60)
    print("[RAW] data/text/raw audit")
    print("=" * 60)
    print(f"txt_files={len(files)}")

    total_chars = 0
    total_page_markers = 0
    total_blank_runs = 0
    empty_files = 0

    for path in files:
        stat = analyze_text_file(path)
        total_chars += stat["chars"]
        total_page_markers += stat["page_markers"]
        total_blank_runs += stat["repeated_blank_runs"]
        if stat["empty"]:
            empty_files += 1
        print(
            f"- {stat['file']}: chars={stat['chars']}, page_markers={stat['page_markers']}, repeated_blank_runs={stat['repeated_blank_runs']}"
        )

    print("\n[RAW SUMMARY]")
    print(f"total_chars={total_chars}")
    print(f"empty_files={empty_files}")
    print(f"total_page_markers={total_page_markers}")
    print(f"total_repeated_blank_runs={total_blank_runs}")

    print("\n" + "=" * 60)
    print("[EVAL] data/text/eval/queries_text_main.jsonl audit")
    print("=" * 60)

    rows = load_eval(EVAL_PATH)
    if not rows:
        print("No eval rows found.")
        return 0

    errors = [r for r in rows if "_error" in r]
    valid_rows = [r for r in rows if "_error" not in r]

    missing_gold = 0
    type_counts = {"A": 0, "B": 0, "C": 0, "UNKNOWN": 0}
    for row in valid_rows:
        q_type = row.get("query_type", "UNKNOWN")
        if q_type not in type_counts:
            q_type = "UNKNOWN"
        type_counts[q_type] += 1

        if not row.get("gold_sources"):
            missing_gold += 1

    print(f"rows={len(rows)} valid={len(valid_rows)} errors={len(errors)}")
    print(f"missing_gold_sources={missing_gold}")
    print(f"type_counts={type_counts}")

    if errors:
        print("\n[PARSE ERRORS]")
        for e in errors:
            print(f"- {e['_error']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
