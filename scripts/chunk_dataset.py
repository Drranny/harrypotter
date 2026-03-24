import argparse
import ast
import json
import os
import re
import sys
from typing import Any, Dict, List

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    LEGACY_PROCESSED_DIR,
    LEGACY_RAW_DIR,
    TEXT_PROCESSED_DIR,
    TEXT_RAW_DIR,
)


TEXT_FILE_EXTENSIONS = {".txt", ".md"}
CODE_FILE_EXTENSIONS = {".py"}


def _first_existing_path(*candidates: str) -> str:
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def parse_args() -> argparse.Namespace:
    default_text_input_dir = _first_existing_path(TEXT_RAW_DIR, LEGACY_RAW_DIR)
    default_output = os.path.join(
        _first_existing_path(TEXT_PROCESSED_DIR, LEGACY_PROCESSED_DIR),
        "chunks.json",
    )

    parser = argparse.ArgumentParser(description="Unified dataset chunker")
    parser.add_argument(
        "--mode",
        choices=["fixed", "line", "token", "structure_text", "structure_code"],
        default="fixed",
        help="Chunking mode",
    )
    parser.add_argument(
        "--text-input-dir",
        default=default_text_input_dir,
        help="Directory for text dataset files",
    )
    parser.add_argument(
        "--code-input-dir",
        default="data/raw_code",
        help="Directory for code dataset files (optional)",
    )
    parser.add_argument(
        "--output",
        default=default_output,
        help="Output path for chunk list JSON",
    )
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    return parser.parse_args()


def read_files(input_dir: str, extensions: set[str]) -> List[str]:
    if not os.path.exists(input_dir):
        return []

    files: List[str] = []
    for root, _, names in os.walk(input_dir):
        for name in names:
            ext = os.path.splitext(name)[1].lower()
            if ext in extensions:
                files.append(os.path.join(root, name))
    return sorted(files)


def extract_text_metadata(fname: str, text: str) -> Dict:
    metadata = {"source_file": fname}

    if fname.startswith("Book") and fname.endswith(".txt"):
        m = re.search(r"Book(\d+)", fname)
        if m:
            metadata.update(
                {
                    "source": "book",
                    "series": "harry_potter",
                    "volume": int(m.group(1)),
                }
            )
        return metadata

    if fname == "hp_spells_list.txt":
        metadata.update({"source": "lore", "topic": "spells"})
        return metadata

    if fname.startswith("harrypotter1_"):
        text_lower = text.lower()
        if any(
            keyword in text_lower
            for keyword in [
                "review",
                "blu-ray",
                "film",
                "movie",
                "cinema",
                "director",
                "actor",
                "performance",
                "screenplay",
            ]
        ):
            review_type = "critic"
            if any(
                keyword in text_lower
                for keyword in ["audience", "viewer", "fan", "rating", "imdb"]
            ):
                review_type = "audience"
            metadata.update(
                {
                    "source": "review",
                    "movie": "harry_potter_1",
                    "type": review_type,
                }
            )
            return metadata

        if any(
            keyword in text_lower
            for keyword in [
                "character",
                "protagonist",
                "harry potter",
                "dumbledore",
                "voldemort",
                "hermione",
                "ron weasley",
            ]
        ):
            metadata.update({"source": "lore", "topic": "character"})
            return metadata

        if any(
            keyword in text_lower
            for keyword in [
                "overview",
                "series",
                "novels",
                "author",
                "j. k. rowling",
                "themes",
            ]
        ):
            metadata.update({"source": "lore", "topic": "overview"})
            return metadata

        if any(
            keyword in text_lower
            for keyword in ["magic", "spell", "wand", "wizard", "wizarding world"]
        ):
            metadata.update({"source": "lore", "topic": "magic"})
            return metadata

    metadata.update({"source": "unknown", "topic": "unknown"})
    return metadata


def split_fixed(text: str, chunk_size: int, overlap: int) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    return splitter.split_text(text)


def split_line(text: str, chunk_size: int, overlap: int) -> List[str]:
    lines = text.splitlines()
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > chunk_size:
            chunks.append("\n".join(current))
            if overlap > 0:
                carry = "\n".join(current)
                carry = carry[-overlap:]
                current = [carry] if carry else []
                current_len = len(carry)
            else:
                current = []
                current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))
    return [c for c in chunks if c.strip()]


def split_token(text: str, chunk_size: int, overlap: int) -> List[str]:
    tokens = text.split()
    if not tokens:
        return []

    chunks: List[str] = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(tokens), step):
        chunk_tokens = tokens[i : i + chunk_size]
        if not chunk_tokens:
            continue
        chunks.append(" ".join(chunk_tokens))
        if i + chunk_size >= len(tokens):
            break
    return chunks


def _sentence_tail(text: str, max_chars: int = 160) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    if len(normalized) <= max_chars:
        return normalized
    return normalized[-max_chars:]


def _sentence_head(text: str, max_chars: int = 220) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars]


def _augment_with_context(context_text: str, content_text: str, chunk_size: int) -> str:
    if not context_text:
        return content_text

    context = _sentence_tail(context_text, max_chars=max(90, chunk_size // 2))
    if not context:
        return content_text

    prefix = f"[CTX] {context}\n"
    # small-size 정책: 길이를 무한히 늘리지 않고, 기존 chunk 대비 최대 1.5배까지만 허용
    max_len = int(chunk_size * 1.5)
    if len(prefix) + len(content_text) > max_len:
        allowed_ctx = max(0, max_len - len(content_text) - len("[CTX] \n"))
        if allowed_ctx <= 0:
            return content_text
        context = context[-allowed_ctx:]
        prefix = f"[CTX] {context}\n"

    return prefix + content_text


def split_structure_text(text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
    # Keep chapter-like blocks first, then paragraph level.
    chapter_blocks = re.split(r"\n\s*(CHAPTER\s+[A-Z0-9]+.*)\n", text, flags=re.IGNORECASE)

    blocks: List[Dict[str, str]] = []
    if len(chapter_blocks) <= 1:
        blocks = [{"chapter_title": "unknown", "body": text}]
    else:
        i = 1
        while i < len(chapter_blocks):
            title = chapter_blocks[i].strip()
            body = chapter_blocks[i + 1] if i + 1 < len(chapter_blocks) else ""
            blocks.append({"chapter_title": title or "unknown", "body": body})
            i += 2

    results: List[Dict[str, Any]] = []
    for block in blocks:
        chapter_title = block["chapter_title"]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", block["body"]) if p.strip()]
        prev_tail = ""

        for para in paragraphs:
            if len(para) <= chunk_size:
                chunk_text = para
                context_augmented = False
                if chunk_size <= 128 and prev_tail:
                    chunk_text = _augment_with_context(prev_tail, para, chunk_size)
                    context_augmented = chunk_text != para

                results.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            "chapter_title": chapter_title,
                            "context_augmented": context_augmented,
                            "split_from_long_paragraph": False,
                            "boundary_truncated": False,
                        },
                    }
                )
                prev_tail = _sentence_tail(para)
                continue

            sub_chunks = split_fixed(para, chunk_size, overlap)
            for idx, sub in enumerate(sub_chunks):
                context_seed = ""
                if chunk_size <= 128:
                    if idx == 0:
                        context_seed = prev_tail
                    else:
                        context_seed = _sentence_head(sub_chunks[idx - 1])

                chunk_text = _augment_with_context(context_seed, sub, chunk_size) if context_seed else sub
                context_augmented = chunk_text != sub

                results.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            "chapter_title": chapter_title,
                            "context_augmented": context_augmented,
                            "split_from_long_paragraph": True,
                            "boundary_truncated": idx < len(sub_chunks) - 1,
                        },
                    }
                )

            prev_tail = _sentence_tail(para)

    return [row for row in results if row.get("text", "").strip()]


def _iter_ast_chunks(tree: ast.AST, source: str) -> List[Dict]:
    chunks: List[Dict] = []
    lines = source.splitlines()

    class _Visitor(ast.NodeVisitor):
        def __init__(self):
            self._stack: List[str] = []

        def _node_label(self, node: ast.AST) -> str:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return f"function:{node.name}"
            if isinstance(node, ast.ClassDef):
                return f"class:{node.name}"
            return node.__class__.__name__.lower()

        def _visit_target(self, node: ast.AST) -> None:
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)
            if start and end:
                snippet = "\n".join(lines[start - 1 : end]).strip()
                if snippet:
                    self._stack.append(self._node_label(node))
                    chunks.append(
                        {
                            "text": snippet,
                            "metadata": {
                                "node_type": node.__class__.__name__,
                                "start_line": start,
                                "end_line": end,
                                "parent": " > ".join(self._stack),
                            },
                        }
                    )
                    self._stack.pop()
                    return
            self.generic_visit(node)

        def _visit_class(self, node: ast.ClassDef) -> None:
            self._stack.append(self._node_label(node))
            
            # 클래스 내부의 '클래스 변수/docstring' 들을 묶어서 클래스 헤더 청크로 만듦
            _NAMED_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            current_group = []
            
            for child in node.body:
                if isinstance(child, _NAMED_DEFS):
                    # 함수를 만나면, 그 전에 모아둔 클래스 변수들을 하나의 청크로 발행
                    if current_group:
                        start = current_group[0].lineno
                        end = current_group[-1].end_lineno
                        snippet = "\n".join(lines[start - 1 : end]).strip()
                        if snippet:
                            chunks.append({
                                "text": snippet,
                                "metadata": {
                                    "node_type": "ClassHeader",
                                    "start_line": start,
                                    "end_line": end,
                                    "parent": " > ".join(self._stack)
                                }
                            })
                        current_group = []
                else:
                    if hasattr(child, "lineno") and hasattr(child, "end_lineno"):
                        current_group.append(child)
            
            # 클래스 끝에 남은 변수들이 있다면 마저 발행
            if current_group:
                start = current_group[0].lineno
                end = current_group[-1].end_lineno
                snippet = "\n".join(lines[start - 1 : end]).strip()
                if snippet:
                    chunks.append({
                        "text": snippet,
                        "metadata": {
                            "node_type": "ClassHeader",
                            "start_line": start,
                            "end_line": end,
                            "parent": " > ".join(self._stack)
                        }
                    })

            # 함수 등 나머지 자식 노드들 순회
            self.generic_visit(node)
            self._stack.pop()

        visit_ClassDef = _visit_class
        visit_FunctionDef = _visit_target
        visit_AsyncFunctionDef = _visit_target

    _Visitor().visit(tree)

    # Post-process: merge short chunks (<= 50 tokens) safely
    MIN_TOKENS = 50
    merged: List[Dict] = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        token_count = len(current["text"].split())
        
        if token_count <= MIN_TOKENS and i + 1 < len(chunks):
            next_chunk = chunks[i + 1]
            current_parent = current.get("metadata", {}).get("parent", "")
            next_parent = next_chunk.get("metadata", {}).get("parent", "")
            current_type = current.get("metadata", {}).get("node_type", "")
            
            # 조건 1: 부모가 완전히 똑같을 때 (같은 고아 그룹, 같은 클래스 헤더 쪼가리 등)
            is_same_parent = (current_parent == next_parent)
            
            # 조건 2: 다음 청크가 내 자식일 때 (내 parent 경로로 시작하는지 검사)
            # 예) current: "class:HTTPAdapter", next: "class:HTTPAdapter > function:send"
            is_parent_child = bool(current_parent) and next_parent.startswith(current_parent + " >")
            
            if is_same_parent or (current_type == "ClassHeader" and is_parent_child):
                # 안전하게 병합!
                next_chunk["text"] = current["text"] + "\n\n" + next_chunk["text"]
                i += 1
                continue
                
        merged.append(current)
        i += 1
    chunks = merged

    # Detect orphan code: top-level statements outside class/function definitions.
    # Group consecutive orphan nodes (split whenever a named def appears between them).
    _NAMED_DEFS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    orphan_groups: List[List[ast.AST]] = []
    current_group: List[ast.AST] = []
    for _node in getattr(tree, "body", []):
        if isinstance(_node, _NAMED_DEFS):
            if current_group:
                orphan_groups.append(current_group)
                current_group = []
        else:
            _start = getattr(_node, "lineno", None)
            _end = getattr(_node, "end_lineno", None)
            if _start and _end:
                current_group.append(_node)
    if current_group:
        orphan_groups.append(current_group)

    for group in orphan_groups:
        group_start = group[0].lineno
        group_end = group[-1].end_lineno
        snippet = "\n".join(lines[group_start - 1 : group_end]).strip()
        if not snippet:
            continue
        chunks.append(
            {
                "text": snippet,
                "metadata": {
                    "node_type": "orphan",
                    "start_line": group_start,
                    "end_line": group_end,
                    "parent": "",
                    "is_orphan": True,
                },
            }
        )

    return chunks


def split_structure_code(text: str) -> List[Dict]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    return _iter_ast_chunks(tree, text)


def chunk_text_file(path: str, mode: str, chunk_size: int, overlap: int) -> List[Dict]:
    fname = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    base_meta = extract_text_metadata(fname, text)

    if mode == "fixed":
        pieces: List[Any] = split_fixed(text, chunk_size, overlap)
    elif mode == "line":
        pieces = split_line(text, chunk_size, overlap)
    elif mode == "token":
        pieces = split_token(text, chunk_size, overlap)
    elif mode == "structure_text":
        pieces = split_structure_text(text, chunk_size, overlap)
    else:
        return []

    rows: List[Dict] = []
    for i, piece in enumerate(pieces):
        if isinstance(piece, dict):
            piece_text = str(piece.get("text", ""))
            piece_meta = piece.get("metadata", {})
        else:
            piece_text = str(piece)
            piece_meta = {}

        if not piece_text.strip():
            continue

        rows.append(
            {
                "chunk_id": i,
                "text": piece_text,
                "source_file": fname,
                **base_meta,
                "chunk_mode": mode,
                "chunk_size": chunk_size,
                "chunk_overlap": overlap,
                "metadata": piece_meta,
            }
        )
    return rows


def chunk_code_file(path: str, mode: str, chunk_size: int, overlap: int) -> List[Dict]:
    fname = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    rows: List[Dict] = []

    if mode == "fixed":
        pieces = split_fixed(text, chunk_size, overlap)
        for i, piece in enumerate(pieces):
            rows.append(
                {
                    "chunk_id": i,
                    "text": piece,
                    "source_file": fname,
                    "source": "code",
                    "chunk_mode": mode,
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                    "metadata": {},
                }
            )
        return rows

    if mode == "line":
        pieces = split_line(text, chunk_size, overlap)
        for i, piece in enumerate(pieces):
            rows.append(
                {
                    "chunk_id": i,
                    "text": piece,
                    "source_file": fname,
                    "source": "code",
                    "chunk_mode": mode,
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                    "metadata": {},
                }
            )
        return rows

    if mode == "token":
        pieces = split_token(text, chunk_size, overlap)
        for i, piece in enumerate(pieces):
            rows.append(
                {
                    "chunk_id": i,
                    "text": piece,
                    "source_file": fname,
                    "source": "code",
                    "chunk_mode": mode,
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                    "metadata": {},
                }
            )
        return rows

    if mode == "structure_code":
        structured = split_structure_code(text)
        for i, obj in enumerate(structured):
            piece_text = obj["text"]
            piece_meta = obj.get("metadata", {})

            # 🌟 [하이브리드 폴백 추가] 청크가 너무 크면 fixed_size로 강제 분할하되 족보(parent)는 유지!
            if len(piece_text) > chunk_size:
                sub_pieces = split_fixed(piece_text, chunk_size, overlap)
                for sub_i, sub_text in enumerate(sub_pieces):
                    # 기존 족보 메타데이터 복사 후 폴백 정보 추가
                    fallback_meta = piece_meta.copy()
                    fallback_meta["fallback_chunked"] = True
                    
                    rows.append(
                        {
                            "chunk_id": f"{i}_{sub_i}",
                            "text": sub_text,
                            "source_file": fname,
                            "source": "code",
                            "chunk_mode": mode,
                            "chunk_size": chunk_size,
                            "chunk_overlap": overlap,
                            "metadata": fallback_meta,
                        }
                    )
            else:
                rows.append(
                    {
                        "chunk_id": str(i),
                        "text": piece_text,
                        "source_file": fname,
                        "source": "code",
                        "chunk_mode": mode,
                        "chunk_size": chunk_size,
                        "chunk_overlap": overlap,
                        "metadata": piece_meta,
                    }
                )
        return rows

    return rows


def main() -> None:
    args = parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    text_files = read_files(args.text_input_dir, TEXT_FILE_EXTENSIONS)
    code_files = read_files(args.code_input_dir, CODE_FILE_EXTENSIONS)

    all_chunks: List[Dict] = []

    # Text modes operate on text dataset.
    if args.mode in {"fixed", "line", "token", "structure_text"}:
        for path in text_files:
            rows = chunk_text_file(path, args.mode, args.chunk_size, args.overlap)
            all_chunks.extend(rows)
            print(f"[TEXT] {os.path.basename(path)}: {len(rows)} chunks")

    # Code mode operates on code dataset, but does not fail if dataset is missing.
    if args.mode in {"fixed", "line", "token", "structure_code"}:
        if not code_files:
            print(f"[WARN] No code files found in {args.code_input_dir}. Writing empty output.")
        for path in code_files:
            rows = chunk_code_file(path, args.mode, args.chunk_size, args.overlap)
            all_chunks.extend(rows)
            print(f"[CODE] {os.path.basename(path)}: {len(rows)} chunks")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"[DONE] mode={args.mode}, chunks={len(all_chunks)}, output={args.output}")


if __name__ == "__main__":
    main()
