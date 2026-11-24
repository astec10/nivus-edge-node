#!/usr/bin/env python3
"""Build and verify a self-contained, data-free Nivus installer bundle."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Iterable


FORMAT_VERSION = 1
PROJECT_NAME = "nivus"
PROFILES = ("master", "worker")
EXCLUDED_COMPONENTS = {
    ".codex",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    "data",
    "secrets",
    "certs",
    "usb-key",
    "work",
    "logs",
    "temp",
    "tmp",
}
SENSITIVE_NAMES = {
    "authorized_keys",
    "known_hosts",
    "credentials.json",
    "service-account.json",
}
SENSITIVE_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
}
SENSITIVE_TRAILING_SUFFIXES = (
    ".db-wal",
    ".db-shm",
    ".db-journal",
    ".sqlite-wal",
    ".sqlite-shm",
    ".sqlite-journal",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".sqlite3-journal",
)
REQUIRED_PAYLOAD_FILES = (
    "docker-compose.yml",
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "deploy/install.sh",
    "deploy/nivus-node-agent.service.example",
    "deploy/portable_usb/configure_runtime.py",
    "deploy/portable_usb/install_nivus.sh",
    "deploy/live-usb/nivus-data-volume-guard",
    "node_agent/agent.py",
)
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class BundleError(RuntimeError):
    """An invalid source tree or installer bundle."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BundleError("caminho inválido no manifesto do pacote.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BundleError("caminho inseguro no manifesto do pacote.")
    return path


def _excluded(relative: PurePosixPath) -> bool:
    if any(part in EXCLUDED_COMPONENTS for part in relative.parts):
        return True
    name = relative.name.lower()
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def _is_sensitive(relative: PurePosixPath) -> bool:
    name = relative.name.lower()
    if name in SENSITIVE_NAMES:
        return True
    if name.startswith(("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa")):
        return True
    if name.endswith(tuple(SENSITIVE_SUFFIXES)):
        return True
    if name.endswith(SENSITIVE_TRAILING_SUFFIXES) or ".log." in name:
        return True
    if name.startswith(".env") and name != ".env.example":
        return True
    if name.endswith("_secret.json") or name.endswith("_secret.yaml"):
        return True
    return False


def _source_commit(source_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        )
        top = Path(result.stdout.strip()).resolve(strict=True)
        if top != source_root:
            raise BundleError("--source-root precisa apontar para a raiz do repositório Git.")
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not COMMIT_RE.fullmatch(commit):
            raise BundleError("o commit de origem não é um SHA Git completo.")
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BundleError("não foi possível consultar o estado Git da origem.") from exc
    if status.strip():
        raise BundleError("a origem precisa estar limpa e commitada; pacote não foi criado.")
    return commit


def _archive_payload(source_root: Path, destination: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=source_root,
        check=True,
        capture_output=True,
    )
    written: list[Path] = []
    try:
        archive = tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:")
    except tarfile.TarError as exc:
        raise BundleError("o Git não gerou um snapshot TAR válido.") from exc

    with archive:
        for member in archive:
            raw_name = member.name.rstrip("/")
            if not raw_name:
                continue
            relative = _safe_relative(raw_name)
            if _is_sensitive(relative):
                raise BundleError(f"arquivo sensível versionado recusado: {relative.as_posix()}")
            if _excluded(relative):
                continue
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise BundleError(f"tipo de arquivo não permitido no pacote: {relative.as_posix()}")
            source = archive.extractfile(member)
            if source is None:
                raise BundleError(f"não foi possível ler {relative.as_posix()} do snapshot Git.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
            written.append(target)
    return written


def _manifest_files(bundle_root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    paths = sorted(bundle_root.rglob("*"), key=lambda item: item.relative_to(bundle_root).as_posix())
    for path in paths:
        if path.is_symlink():
            raise BundleError(f"link simbólico não permitido no pacote: {path.relative_to(bundle_root)}")
        if not path.is_file():
            continue
        relative = path.relative_to(bundle_root).as_posix()
        if relative == "bundle_manifest.json":
            continue
        entries.append({"path": relative, "size": path.stat().st_size, "sha256": _sha256(path)})
    return entries


def _validate_manifest_shape(manifest: object) -> dict:
    expected = {
        "format_version",
        "project",
        "bundle_version",
        "source_commit",
        "profiles",
        "payload_mode",
        "files",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise BundleError("estrutura do manifesto inválida.")
    if manifest["format_version"] != FORMAT_VERSION or manifest["project"] != PROJECT_NAME:
        raise BundleError("versão ou projeto do manifesto não reconhecido.")
    if not isinstance(manifest["bundle_version"], str) or not VERSION_RE.fullmatch(manifest["bundle_version"]):
        raise BundleError("versão do pacote inválida.")
    if not isinstance(manifest["source_commit"], str) or not COMMIT_RE.fullmatch(manifest["source_commit"]):
        raise BundleError("commit de origem inválido no manifesto.")
    if manifest["profiles"] != list(PROFILES) or manifest["payload_mode"] != "source_snapshot":
        raise BundleError("perfis ou modo do pacote não reconhecidos.")
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise BundleError("o manifesto não lista arquivos do pacote.")
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise BundleError("entrada de arquivo inválida no manifesto.")
        relative = _safe_relative(item["path"])
        if relative.as_posix() == "bundle_manifest.json" or item["path"] in seen:
            raise BundleError("arquivo duplicado ou manifesto autorreferente.")
        seen.add(item["path"])
        if not isinstance(item["size"], int) or isinstance(item["size"], bool) or item["size"] < 0:
            raise BundleError("tamanho de arquivo inválido no manifesto.")
        if not isinstance(item["sha256"], str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise BundleError("SHA-256 inválido no manifesto.")
    if [item["path"] for item in files] != sorted(seen):
        raise BundleError("a lista de arquivos do manifesto precisa estar ordenada.")
    return manifest


def verify_bundle(bundle_root: Path) -> int:
    if bundle_root.is_symlink() or not bundle_root.is_dir():
        raise BundleError("o pacote precisa ser uma pasta real.")
    bundle_root = bundle_root.resolve(strict=True)
    manifest_path = bundle_root / "bundle_manifest.json"
    try:
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise BundleError("bundle_manifest.json ausente ou inválido.")
        manifest = _validate_manifest_shape(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleError("não foi possível ler o manifesto JSON do pacote.") from exc

    listed = {item["path"] for item in manifest["files"]}
    actual: set[str] = set()
    for path in bundle_root.rglob("*"):
        if path.is_symlink():
            raise BundleError(f"link simbólico inesperado no pacote: {path.relative_to(bundle_root)}")
        if path.is_file():
            actual.add(path.relative_to(bundle_root).as_posix())
    actual.discard("bundle_manifest.json")
    if actual != listed:
        extras = sorted(actual - listed)
        missing = sorted(listed - actual)
        detail = []
        if extras:
            detail.append("extras=" + ",".join(extras[:5]))
        if missing:
            detail.append("ausentes=" + ",".join(missing[:5]))
        raise BundleError("conteúdo do pacote diverge do manifesto (" + "; ".join(detail) + ").")

    for item in manifest["files"]:
        relative = _safe_relative(item["path"])
        path = bundle_root.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise BundleError(f"arquivo listado ausente ou inválido: {relative.as_posix()}")
        if path.stat().st_size != item["size"] or _sha256(path) != item["sha256"]:
            raise BundleError(f"integridade não confere: {relative.as_posix()}")
    required = {
        "install_nivus.sh",
        "bundle_manifest.schema.json",
        *(f"payload/{path}" for path in REQUIRED_PAYLOAD_FILES),
    }
    if not required.issubset(listed):
        raise BundleError("o pacote não contém todos os arquivos necessários para os perfis Master e Worker.")
    return len(listed)


def _write_archive(bundle_root: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(bundle_root.rglob("*")):
            relative = path.relative_to(bundle_root.parent).as_posix()
            archive.add(path, arcname=relative, recursive=False)


def build_bundle(source_root: Path, output_dir: Path, version: str) -> tuple[Path, Path, Path]:
    source_root = source_root.resolve(strict=True)
    if not source_root.is_dir():
        raise BundleError("--source-root precisa ser uma pasta.")
    if not VERSION_RE.fullmatch(version):
        raise BundleError("use uma versão simples, por exemplo 0.1.0.")
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise BundleError("--output-dir precisa ficar fora do repositório de origem.")
    if output_dir.exists():
        raise BundleError("--output-dir já existe; escolha uma pasta nova para não sobrescrever artefatos.")

    commit = _source_commit(source_root)
    bundle_root = output_dir / f"nivus-install-bundle-{version}"
    payload_root = bundle_root / "payload"
    payload_root.mkdir(parents=True)
    try:
        _archive_payload(source_root, payload_root)
        for relative in REQUIRED_PAYLOAD_FILES:
            if not (payload_root / relative).is_file():
                raise BundleError(f"arquivo de instalação obrigatório ausente: {relative}")
        shutil.copyfile(
            payload_root / "deploy/portable_usb/install_nivus.sh",
            bundle_root / "install_nivus.sh",
        )
        shutil.copyfile(
            payload_root / "deploy/portable_usb/bundle_manifest.schema.json",
            bundle_root / "bundle_manifest.schema.json",
        )
        manifest = {
            "format_version": FORMAT_VERSION,
            "project": PROJECT_NAME,
            "bundle_version": version,
            "source_commit": commit,
            "profiles": list(PROFILES),
            "payload_mode": "source_snapshot",
            "files": _manifest_files(bundle_root),
        }
        manifest_path = bundle_root / "bundle_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        count = verify_bundle(bundle_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_path = output_dir / f"{bundle_root.name}.tar.gz"
        _write_archive(bundle_root, archive_path)
        checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
        checksum_path.write_text(f"{_sha256(archive_path)}  {archive_path.name}\n", encoding="ascii")
        print(f"Pacote verificado: {count} arquivos; versão {version}; origem {commit}.")
        return bundle_root, archive_path, checksum_path
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="cria a pasta instalável, o arquivo TAR.GZ e o SHA-256.")
    build.add_argument("--source-root", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--version", required=True)
    verify = commands.add_parser("verify", help="confere a lista e os hashes SHA-256 do pacote.")
    verify.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            bundle, archive, checksum = build_bundle(args.source_root, args.output_dir, args.version)
            print(f"Pasta: {bundle}")
            print(f"Arquivo: {archive}")
            print(f"SHA-256: {checksum}")
        else:
            count = verify_bundle(args.bundle)
            print(f"Pacote íntegro: {count} arquivos verificados.")
        return 0
    except (BundleError, OSError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
