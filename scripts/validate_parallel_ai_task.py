#!/usr/bin/env python3
"""Validate a Nivus parallel-work issue before queuing it for manual assignment."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath

REQUIRED = (
    "Objetivo",
    "Skills/documentação de domínio",
    "Módulo responsável e arquivos permitidos",
    "Contexto e contratos",
    "Critérios de aceite",
    "Validação esperada",
    "Dependências, conflitos e ordem",
    "Classificação de dados",
    "Risco",
    "Responsável humano pela revisão",
)
SKILLS = {
    "nivus-project-guide",
    "nivus-ai-dev-workflow",
    "nivus-ai-provider-connectors",
    "nivus-backend-api",
    "nivus-dashboard-ui",
    "nivus-edge-operations",
    "nivus-hardware-telemetry",
    "nivus-home-automation",
    "nivus-local-ai-knowledge",
    "nivus-node-registry",
    "nivus-task-orchestration",
}
ALLOWED_DATA_CLASSES = {"Código/documentação pública", "Dados sintéticos"}
ALLOWED_RISKS = {"Baixo", "Médio — integração/revisão humana antes de merge"}
FORBIDDEN_PARTS = {
    ".env",
    "secrets",
    "data",
    "logs",
    "node_modules",
    ".git",
    ".venv",
    "authorized_keys",
    "known_hosts",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
}
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db", ".log")
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


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
    return {name: "\n".join(lines).strip() for name, lines in found.items()}


def selected_skills(section: str) -> set[str]:
    selected = set()
    for line in section.splitlines():
        match = re.match(r"^\s*-\s*\[x\]\s+([a-z0-9-]+)\b", line, re.IGNORECASE)
        if match:
            selected.add(match.group(1).casefold())
    return selected


def allowed_paths(section: str) -> list[str]:
    lines = section.splitlines()
    path_header = next(
        (index for index, line in enumerate(lines) if line.strip().casefold() == "arquivos permitidos:"),
        None,
    )
    if path_header is None:
        return []
    result = []
    for line in lines[path_header + 1 :]:
        value = line.strip()
        if not value:
            continue
        if value.casefold().startswith("dono do contrato"):
            break
        value = value.lstrip("-* ").strip().strip("`")
        if value:
            result.append(value)
    return result


def validate(body: str, *, confirmed_public_or_synthetic: bool) -> list[str]:
    problems: list[str] = []
    values = sections(body)

    for name in REQUIRED:
        if not values.get(name):
            problems.append(f"Seção obrigatória vazia/ausente: {name}")

    if not confirmed_public_or_synthetic:
        problems.append("Um mantenedor precisa confirmar a revisão de escopo e classificação dos dados.")
    if SECRET_RE.search(body) or PRIVATE_KEY_RE.search(body):
        problems.append("A Issue contém um padrão semelhante a segredo; remova credenciais antes de enfileirar.")

    data_class = values.get("Classificação de dados", "")
    if data_class not in ALLOWED_DATA_CLASSES:
        problems.append("A fila aceita somente código/documentação pública ou dados sintéticos.")

    risk = values.get("Risco", "")
    if risk not in ALLOWED_RISKS:
        problems.append("Tarefas de alto risco não entram na fila automatizada.")

    selected = selected_skills(values.get("Skills/documentação de domínio", ""))
    if not selected:
        problems.append("Selecione ao menos uma skill/documentação de domínio.")
    unknown = selected - SKILLS
    if unknown:
        problems.append(f"A Issue selecionou skills desconhecidas: {', '.join(sorted(unknown))}.")

    module = values.get("Módulo responsável e arquivos permitidos", "")
    paths = allowed_paths(module)
    if not paths:
        problems.append("Liste caminhos exatos no campo Arquivos permitidos.")
    if len(paths) != len(set(paths)):
        problems.append("Arquivos permitidos não pode repetir caminhos.")

    for entry in paths:
        candidate = PurePosixPath(entry)
        parts = entry.split("/")
        folded_parts = [part.casefold() for part in parts]
        if (
            entry.startswith("/")
            or "\\" in entry
            or ":" in entry
            or candidate.as_posix() != entry
            or any(part in {"", ".", ".."} for part in parts)
            or any(char in entry for char in "*?[]")
            or any(ord(char) < 32 for char in entry)
        ):
            problems.append(f"Caminho amplo ou inválido: {entry}")
        if entry.casefold().startswith(".github/workflows/"):
            problems.append(f"Mudanças em workflows exigem tarefa/revisão separada: {entry}")
        if any(part in FORBIDDEN_PARTS for part in folded_parts) or any(
            entry.casefold().endswith(suffix) for suffix in SENSITIVE_SUFFIXES
        ):
            problems.append(f"Caminho sensível não pode entrar na fila pública: {entry}")

    owner = values.get("Responsável humano pela revisão", "")
    if not re.search(r"@[A-Za-z0-9-]{1,39}", owner):
        problems.append("Informe uma conta GitHub no responsável humano pela revisão.")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Corpo da Issue; por padrão lê stdin")
    parser.add_argument(
        "--confirmed-public-or-synthetic",
        action="store_true",
        help="Confirma que a pessoa mantenedora revisou os dados e o escopo públicos/sintéticos",
    )
    args = parser.parse_args()
    body = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    problems = validate(body, confirmed_public_or_synthetic=args.confirmed_public_or_synthetic)
    if problems:
        for problem in problems:
            print(f"ERRO: {problem}", file=sys.stderr)
        return 1
    print("Issue validada e pronta para fila manual; nenhum modelo foi chamado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
