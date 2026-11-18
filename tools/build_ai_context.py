#!/usr/bin/env python3
"""Build a model-independent lexical index from Nivus knowledge sources."""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
TOPICS = KNOWLEDGE / "topics"
CATALOG = KNOWLEDGE / "catalog" / "video_sources.jsonl"
INDEX = KNOWLEDGE / "index" / "records.jsonl"
TERMS = KNOWLEDGE / "index" / "terms.json"
DOCS = (
    "docs/AI_CONTEXT.md",
    "docs/AI_PROVIDER_CONNECTORS.md",
    "docs/AI_WORKFLOW.md",
    "docs/AI_DEVELOPMENT_ORCHESTRATION.md",
    "docs/AI_EXECUTOR_IMPLEMENTATION.md",
    "docs/AI_MODULE_WORKPLAN.md",
    "docs/VIDEO_RESEARCH_INDEX.md",
    "docs/MODULE_MAP.md",
    "docs/NODE_REGISTRY.md",
    "docs/DESKTOP_ASSISTANT.md",
    "docs/HARDWARE_TELEMETRY.md",
    "docs/PROJECT_STATUS.md",
    "docs/PROJECT_ROADMAP.md",
    "docs/VISION.md",
)
TOKEN_RE = re.compile(r"C\+\+|[A-Za-z0-9_]+|[^\W_]+", re.UNICODE)
REQUIRED = ("id", "title", "topic", "source", "verified_on", "confidence")
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def tokenize(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return sorted({match.group(0) for match in TOKEN_RE.finditer(normalized)})


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError(f"Frontmatter ausente: {path.relative_to(ROOT)}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"Frontmatter sem fechamento: {path.relative_to(ROOT)}") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().casefold()] = value.strip().strip('"').strip("'")
    if not metadata or all(value.startswith("<") for value in metadata.values()):
        return None

    missing = [key for key in REQUIRED if not metadata.get(key) or metadata[key].startswith("<")]
    body = "\n".join(lines[end + 1 :]).strip()
    if missing or not body:
        raise ValueError(f"Nota incompleta {path.relative_to(ROOT)}: {', '.join(missing or ['conteúdo'])}")
    if SECRET_RE.search(text) or PRIVATE_KEY_RE.search(text):
        raise ValueError(f"Padrão semelhante a credencial em {path.relative_to(ROOT)}")

    tags = [tag.strip() for tag in metadata.get("tags", "").split(",") if tag.strip()]
    searchable = " ".join([metadata["title"], metadata["topic"], *tags, body])
    return {
        **metadata,
        "tags": tags,
        "source_file": path.relative_to(ROOT).as_posix(),
        "content": body,
        "tokens": tokenize(searchable),
        "record_type": "topic-note",
    }


def load_records() -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()

    for relative in DOCS:
        path = ROOT / relative
        content = path.read_text(encoding="utf-8").strip()
        title = next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), path.stem)
        records.append(
            {
                "id": f"doc-{path.stem.casefold().replace('_', '-')}",
                "title": title,
                "topic": path.stem.casefold().replace("_", "-"),
                "source": relative,
                "source_file": relative,
                "content": content,
                "confidence": "project-source",
                "tokens": tokenize(content),
                "record_type": "project-document",
            }
        )

    for path in sorted(TOPICS.rglob("*.md")):
        record = parse_frontmatter(path)
        if record is not None:
            records.append(record)

    if CATALOG.exists():
        for line_number, line in enumerate(CATALOG.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            source = json.loads(line)
            required = ("id", "title", "url", "theme", "status", "claim_summary", "search_terms")
            missing = [key for key in required if key not in source]
            if missing:
                raise ValueError(f"Catálogo {CATALOG.name}:{line_number} sem {', '.join(missing)}")
            searchable = " ".join(
                [source["title"], source["theme"], source["status"], source["claim_summary"], *source["search_terms"]]
            )
            records.append(
                {
                    **source,
                    "source_file": CATALOG.relative_to(ROOT).as_posix(),
                    "tokens": tokenize(searchable),
                    "record_type": "video-source",
                }
            )

    for record in records:
        if record["id"] in seen:
            raise ValueError(f"ID de conhecimento duplicado: {record['id']}")
        seen.add(record["id"])
    return records


def rendered_indexes(records: list[dict]) -> dict[Path, str]:
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    index_content = "\n".join(lines) + ("\n" if lines else "")
    postings: dict[str, list[str]] = defaultdict(list)
    for record in records:
        for token in record["tokens"]:
            postings[token].append(record["id"])
    return {
        INDEX: index_content,
        TERMS: json.dumps(postings, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }


def build_indexes(records: list[dict], check: bool = False) -> bool:
    expected = rendered_indexes(records)
    if check:
        stale = [path.relative_to(ROOT).as_posix() for path, content in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            print("Índice desatualizado ou ausente: " + ", ".join(stale))
            if INDEX in expected and INDEX.exists():
                actual_lines = INDEX.read_text(encoding="utf-8").splitlines()
                expected_lines = expected[INDEX].splitlines()
                if len(actual_lines) != len(expected_lines):
                    print(f"Registros: atual={len(actual_lines)}, esperado={len(expected_lines)}")
                for line_number in range(max(len(actual_lines), len(expected_lines))):
                    actual_line = actual_lines[line_number] if line_number < len(actual_lines) else None
                    expected_line = expected_lines[line_number] if line_number < len(expected_lines) else None
                    if actual_line == expected_line:
                        continue
                    try:
                        actual_record = json.loads(actual_line) if actual_line else {}
                        expected_record = json.loads(expected_line) if expected_line else {}
                    except json.JSONDecodeError:
                        print(f"Primeira divergência em knowledge/index/records.jsonl, linha {line_number + 1}: linha JSON inválida.")
                        break
                    fields = sorted(
                        key for key in set(actual_record) | set(expected_record)
                        if actual_record.get(key) != expected_record.get(key)
                    )
                    print(
                        f"Primeira divergência em knowledge/index/records.jsonl, linha {line_number + 1}: "
                        f"atual={actual_record.get('id', '<ausente>')}, "
                        f"esperado={expected_record.get('id', '<ausente>')}, campos={', '.join(fields) or 'ordem/serialização'}."
                    )
                    if "tokens" in fields:
                        actual_tokens = set(actual_record.get("tokens", []))
                        expected_tokens = set(expected_record.get("tokens", []))
                        print(
                            "Tokens divergentes: "
                            f"somente atuais={len(actual_tokens - expected_tokens)}, "
                            f"somente esperados={len(expected_tokens - actual_tokens)}."
                        )
                    if "content" in fields:
                        print(
                            "Tamanhos do conteúdo: "
                            f"atual={len(actual_record.get('content', ''))}, "
                            f"esperado={len(expected_record.get('content', ''))}."
                        )
                    break
            print("Execute python3 tools/build_ai_context.py e versione o resultado.")
            return False
        return True
    for path, content in expected.items():
        atomic_write(path, content)
    return True


def search(records: list[dict], query: str, limit: int) -> int:
    terms = set(tokenize(query))
    if not terms:
        print("Informe termos de busca.")
        return 2
    matches = []
    for record in records:
        overlap = terms.intersection(record["tokens"])
        if overlap:
            matches.append((len(overlap) / len(terms), record))
    matches.sort(key=lambda item: (-item[0], item[1]["id"]))
    for score, record in matches[:limit]:
        print(f"{score:.2f}\t{record['id']}\t{record['title']}\t{record.get('theme', record.get('topic'))}\t{record['status'] if 'status' in record else record['confidence']}")
    if not matches:
        print("Nenhum registro corresponde aos termos.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Busca lexical nos registros e notas temáticas")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--check", action="store_true", help="Falha se os índices versionados estiverem desatualizados")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit precisa ser positivo")
    records = load_records()
    if not build_indexes(records, check=args.check):
        return 1
    print(f"Registros indexados: {len(records)}")
    print(f"Índice: {INDEX.relative_to(ROOT)}")
    print(f"Termos: {TERMS.relative_to(ROOT)}")
    return search(records, args.query, args.limit) if args.query else 0


if __name__ == "__main__":
    raise SystemExit(main())
