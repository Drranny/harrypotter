"""
Build paragraph-level corpus with stable paragraph IDs for gold labeling.

Usage:
    python3 scripts/build_paragraph_corpus.py \
      --input-dir data/text/raw \
      --output data/text/processed/paragraphs.json
"""

import argparse
import json
import os
import re
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build paragraph-level corpus from text files")
    parser.add_argument("--input-dir", default="data/text/raw", help="Input raw text directory")
    parser.add_argument(
        "--output",
        default="data/text/processed/paragraphs.json",
        help="Output paragraph JSON path",
    )
    return parser.parse_args()


def _book_num_from_filename(filename: str) -> int | None:
    m = re.search(r"Book(\d+)", filename, flags=re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


def _is_chapter_title(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    if re.match(r"^(CHAPTER|Chapter)\b", text):
        return True
    if len(text) <= 80 and text.isupper() and re.search(r"[A-Z]", text):
        return True
    return False


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        if re.search(r"Page\s*\|\s*\d+", line, flags=re.IGNORECASE):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines)


def _split_paragraphs_with_chapter(text: str) -> List[Tuple[int, str]]:
    lines = text.split("\n")
    chapter_num = 0
    current_para: List[str] = []
    rows: List[Tuple[int, str]] = []

    def flush_para() -> None:
        nonlocal current_para
        if not current_para:
            return
        paragraph = "\n".join(current_para).strip()
        if paragraph:
            rows.append((max(chapter_num, 1), paragraph))
        current_para = []

    for line in lines:
        stripped = line.strip()
        if _is_chapter_title(stripped):
            flush_para()
            chapter_num += 1
            continue

        if stripped == "":
            flush_para()
            continue

        current_para.append(line)

    flush_para()
    return rows


def build_rows(path: str) -> List[Dict]:
    fname = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    cleaned = _clean_text(text)
    para_rows = _split_paragraphs_with_chapter(cleaned)

    book_num = _book_num_from_filename(fname)
    rows: List[Dict] = []
    chapter_para_counter: Dict[int, int] = {}

    for chapter, paragraph in para_rows:
        chapter_para_counter[chapter] = chapter_para_counter.get(chapter, 0) + 1
        para_idx = chapter_para_counter[chapter]

        if book_num is not None:
            paragraph_id = f"book_{book_num}_chapter_{chapter}_paragraph_{para_idx}"
        else:
            stem = os.path.splitext(fname)[0].lower()
            paragraph_id = f"{stem}_chapter_{chapter}_paragraph_{para_idx}"

        rows.append(
            {
                "paragraph_id": paragraph_id,
                "source_file": fname,
                "book": book_num,
                "chapter": chapter,
                "paragraph_index": para_idx,
                "text": paragraph,
            }
        )

    return rows


def main() -> int:
    args = parse_args()
    if not os.path.exists(args.input_dir):
        print(f"[ERROR] input directory not found: {args.input_dir}")
        return 1

    all_rows: List[Dict] = []
    for name in sorted(os.listdir(args.input_dir)):
        path = os.path.join(args.input_dir, name)
        if not os.path.isfile(path) or not name.lower().endswith(".txt"):
            continue
        rows = build_rows(path)
        all_rows.extend(rows)
        print(f"[PARA] {name}: {len(rows)}")

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"[DONE] paragraphs={len(all_rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
