#!/usr/bin/env python3
"""Validate a public GitHub issue before adding it to the AI task queue."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath

REQUIRED = (
    "Objective",
    "Acceptance criteria",
    "Allowed paths",
    "Module",
    "Risk",
    "Data classification",
    "Maximum runtime in minutes",
    "External model budget",
    "Human owner",
    "Review gate",
)
FORBIDDEN_PATH_PARTS = {
    ".env",
    "secrets",
    "data",
    "logs",
    "node_modules",
    ".git",
    ".venv",
}
FORBIDDEN_NAMES = {
    "authorized_keys",
    "known_hosts",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
}
SENSITIVE_PREFIXES = ("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa", "secret", "credentials")
SENSITIVE_SUFFIXES = (
    ".pem",
    ".key",
    ".crt",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".db-wal",
    ".db-shm",
    ".log",
)


def sections(body: str) -> dict[str, str]:
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        match = re.match(r"^###\s+(.+?)\s*$", line)
        if match:
            current = match.group(1)
            found.setdefault(current, [])
        elif current:
            found[current].append(line)
    return {key: "\n".join(value).strip() for key, value in found.items()}


def runtime_minutes(body: str) -> int:
    raw = sections(body).get("Maximum runtime in minutes", "")
    if not re.fullmatch(r"\s*\d{1,2}\s*", raw):
        raise ValueError("Maximum runtime precisa ser um número entre 1 e 15 minutos.")
    value = int(raw)
    if not 1 <= value <= 15:
        raise ValueError("Maximum runtime precisa ser um número entre 1 e 15 minutos.")
    return value


def validate(body: str, *, require_free_tier: bool = False) -> list[str]:
    problems: list[str] = []
    values = sections(body)
    for name in REQUIRED:
        if not values.get(name):
            problems.append(f"Seção obrigatória vazia/ausente: {name}")

    data_class = values.get("Data classification", "")
    if data_class not in {"public source code and public documentation", "synthetic test data only"}:
        problems.append("A fila pública aceita somente código/documentação pública ou dados sintéticos.")

    budget = values.get("External model budget", "")
    if budget not in {
        "no model call — intake only",
        "free-tier model call — public/synthetic content only",
    }:
        problems.append("A fila aceita somente intake ou chamada free-tier com dados públicos/sintéticos.")
    elif require_free_tier and budget != "free-tier model call — public/synthetic content only":
        problems.append("A chamada de modelo requer o orçamento free-tier explicitamente selecionado.")

    risk = values.get("Risk", "").casefold()
    if risk == "high":
        problems.append("Tarefas de alto risco exigem execução humana e não podem entrar na fila automática.")
    elif risk not in {"low", "medium"}:
        problems.append("Risk precisa ser low ou medium para entrar na fila automática.")

    runtime = values.get("Maximum runtime in minutes", "")
    if not re.fullmatch(r"\s*\d{1,2}\s*", runtime) or not 1 <= int(runtime) <= 15:
        problems.append("Maximum runtime precisa ser um número entre 1 e 15 minutos.")

    allowed_paths = values.get("Allowed paths", "")
    entries = [line.strip().lstrip("-*").strip().strip("` ") for line in allowed_paths.splitlines() if line.strip()]
    if not entries:
        problems.append("Allowed paths precisa listar caminhos exatos do repositório.")
    if len(set(entries)) != len(entries):
        problems.append("Allowed paths não pode conter caminhos duplicados.")
    for entry in entries:
        path = entry
        candidate = PurePosixPath(path)
        parts = path.split("/")
        if (
            path.startswith("/")
            or "\\" in path
            or ":" in path
            or candidate.as_posix() != path
            or any(part in {"", ".", ".."} for part in parts)
            or any(c in path for c in "*?[]")
            or any(ord(c) < 32 for c in path)
        ):
            problems.append(f"Caminho amplo ou inválido em Allowed paths: {entry}")
        folded_parts = [part.casefold() for part in parts]
        if path.casefold().startswith(".github/workflows/"):
            problems.append(f"Workflows exigem alteração humana separada: {entry}")
        if any(
            part in FORBIDDEN_PATH_PARTS
            or part in FORBIDDEN_NAMES
            or part.startswith(SENSITIVE_PREFIXES)
            or part.startswith(".env.")
            or part.endswith(SENSITIVE_SUFFIXES)
            or part.endswith((".log.1", ".log.2", ".log.gz"))
            for part in folded_parts
        ):
            problems.append(f"Caminho sensível não pode entrar na fila pública: {entry}")

    owner = values.get("Human owner", "")
    if not re.search(r"@[A-Za-z0-9-]{1,39}", owner):
        problems.append("Human owner precisa informar uma conta GitHub como @username.")

    review_gate = values.get("Review gate", "")
    if not re.search(r"(?im)^\s*-\s*\[x\]\s*I understand that a human must review the PR", review_gate):
        problems.append("A confirmação de revisão humana é obrigatória.")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Arquivo com o corpo da issue; por padrão lê stdin")
    parser.add_argument("--require-free-tier", action="store_true", help="Exige autorização explícita para uma chamada free-tier")
    parser.add_argument("--print-runtime-minutes", action="store_true", help="Valida e imprime somente o limite de execução da issue")
    args = parser.parse_args()
    body = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    problems = validate(body, require_free_tier=args.require_free_tier)
    if problems:
        for problem in problems:
            print(f"ERRO: {problem}", file=sys.stderr)
        return 1
    if args.print_runtime_minutes:
        print(runtime_minutes(body))
        return 0
    print("Issue válida para a fila de intake; nenhum modelo foi chamado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
