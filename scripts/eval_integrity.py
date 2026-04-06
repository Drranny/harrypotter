#!/usr/bin/env python3
"""Evaluate structural integrity of code chunk metadata files.

Metrics:
- Syntax Error (%)
- Orphan Code (%)
"""

import ast
import json
import os
import textwrap
from typing import Dict, List, Optional


def is_orphan_heuristic(code_text: str) -> bool:
    """Heuristic orphan detection for fixed chunks without reliable metadata."""
    lines = code_text.splitlines()
    first_line = next((line for line in lines if line.strip()), "")

    if not first_line:
        return False

    if not first_line.startswith((" ", "\t")):
        return False

    stripped = first_line.lstrip()
    if stripped.startswith(("def ", "class ", "@", '"""', "'''", "#")):
        return False

    return True


def check_syntax(code_text: str) -> bool:
    """Run 2-step parsing to reduce false syntax errors on partial chunks."""
    dedented = textwrap.dedent(code_text)

    try:
        ast.parse(dedented)
        return True
    except SyntaxError:
        pass

    wrapped_lines = [f"    {line}" for line in dedented.splitlines()]
    wrapped = "def _wrapper():\n" + "\n".join(wrapped_lines)

    try:
        ast.parse(wrapped)
        return True
    except SyntaxError:
        return False


def build_files_to_check() -> List[Dict[str, str]]:
    """Build canonical file mapping for Jina metadata files."""
    checks: List[Dict[str, str]] = []

    for size in (1500, 500, 256, 128):
        checks.append(
            {
                "method": f"structure_{size}_jina",
                "mode": "structure",
                # 새로 만든 jina 파일을 바라보도록 경로 수정!
                "path": f"data/processed/code_structure_{size}_jina_metadata.json",
                "fallback": f"data/processed/code_structure_{size}_metadata.json",
            }
        )
        checks.append(
            {
                "method": f"fixed_{size}_jina",
                "mode": "fixed",
                # 새로 만든 jina 파일을 바라보도록 경로 수정!
                "path": f"data/processed/code_fixed_{size}_jina_metadata.json",
                "fallback": f"data/processed/code_fixed_{size}_metadata.json",
            }
        )

    return checks


def resolve_existing_path(path: str, fallback: str) -> Optional[str]:
    if os.path.exists(path):
        return path
    if fallback and os.path.exists(fallback):
        return fallback
    return None


def evaluate_file(path: str, mode: str) -> Dict[str, float]:
    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    total = len(chunks)
    if total == 0:
        return {
            "total": 0,
            "syntax_error_count": 0,
            "syntax_error_pct": 0.0,
            "orphan_count": 0,
            "orphan_pct": 0.0,
        }

    syntax_error_count = 0
    orphan_count = 0

    for chunk in chunks:
        text = chunk.get("text", "")
        metadata = chunk.get("metadata", {}) or {}

        if not check_syntax(text):
            syntax_error_count += 1
                
        if mode == "structure":
            if "is_orphan" in metadata:
                is_orphan = bool(metadata.get("is_orphan"))
            else:
                is_orphan = is_orphan_heuristic(text)
        else:
            # fixed 모드는 항상 휴리스틱
            is_orphan = is_orphan_heuristic(text)

        if is_orphan:
            orphan_count += 1

    return {
        "total": total,
        "syntax_error_count": syntax_error_count,
        "syntax_error_pct": (syntax_error_count / total) * 100.0,
        "orphan_count": orphan_count,
        "orphan_pct": (orphan_count / total) * 100.0,
    }


def format_table(rows: List[Dict[str, str]]) -> str:
    headers = ["Chunking Method", "Total Chunks", "Syntax Error (%)", "Orphan Code (%)"]

    method_width = max(len(headers[0]), *(len(r["method"]) for r in rows))
    total_width = max(len(headers[1]), *(len(str(r["total"])) for r in rows))
    syntax_width = max(len(headers[2]), *(len(r["syntax"]) for r in rows))
    orphan_width = max(len(headers[3]), *(len(r["orphan"]) for r in rows))

    header_line = (
        f"{headers[0]:<{method_width}}  "
        f"{headers[1]:>{total_width}}  "
        f"{headers[2]:>{syntax_width}}  "
        f"{headers[3]:>{orphan_width}}"
    )
    separator = "-" * len(header_line)

    body_lines = []
    for row in rows:
        body_lines.append(
            f"{row['method']:<{method_width}}  "
            f"{row['total']:>{total_width}}  "
            f"{row['syntax']:>{syntax_width}}  "
            f"{row['orphan']:>{orphan_width}}"
        )

    return "\n".join([header_line, separator, *body_lines])


def main() -> int:
    files_to_check = build_files_to_check()
    rows: List[Dict[str, str]] = []
    output: Dict = {}  # JSON 저장용

    for item in files_to_check:
        resolved_path = resolve_existing_path(item["path"], item["fallback"])
        if not resolved_path:
            print(f"[WARN] Missing file: {item['path']}")
            continue

        result = evaluate_file(resolved_path, item["mode"])
        
        rows.append({
            "method": item["method"],
            "total": str(result["total"]),
            "syntax": f"{result['syntax_error_pct']:.2f}%",
            "orphan": f"{result['orphan_pct']:.2f}%",
        })
        
        output[item["method"]] = result  # 같은 result 재사용

    if not rows:
        print("[ERROR] No valid files to evaluate.")
        return 1

    os.makedirs("results", exist_ok=True)
    with open("results/integrity_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(format_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())