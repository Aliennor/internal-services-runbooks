#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


README_MARKER_START = "<!-- CURRENT_RUNBOOKS_START -->"
README_MARKER_END = "<!-- CURRENT_RUNBOOKS_END -->"
DATE_RE = re.compile(r"(20\d{2}_\d{2}_\d{2})")
PUBLIC_TOPIC_PREFIXES = (
    "RUNBOOK_BANKA_START_HERE_",
    "RUNBOOK_BANKA_DEV108_FULL_FROM_PODMAN_AND_RAGFLOW_",
    "RUNBOOK_BANKA_PROD_FULL_106_107_FROM_PODMAN_AND_RAGFLOW_",
    "RUNBOOK_BANKA_DNS_TLS_CUTOVER_",
    "RUNBOOK_BANKA_PROD_106_107_INTERVM_SSH_TRUST_",
    "RUNBOOK_BANKA_ENCRYPTED_CONFIG_IMAGE_",
    "RUNBOOK_BANKA_RAGFLOW_DATA_EXPORT_FROM_ZT_ARF_DEV_",
    "RUNBOOK_BANKA_RAGFLOW_PROFILE_QDRANT_NGINX_RECOVERY_",
    "RUNBOOK_BANKA_DEV108_HTTPS_LITELLM_CUTOVER_",
    "RUNBOOK_BANKA_DEV108_R33_POST_INSTALL_TRIAGE_",
)
SANITIZE_REPLACEMENTS = (
    ("Authorization: Bearer sk-ziraat2025", "Authorization: Bearer <LITELLM_MASTER_KEY>"),
    ("litellm_password", "<LITELLM_DB_PASSWORD>"),
    ("langfuse_password", "<LANGFUSE_DB_PASSWORD>"),
    ("miniosecret", "<MINIO_SECRET>"),
    ("myredissecret", "<REDIS_AUTH>"),
    ("mysecret", "<NEXTAUTH_SECRET>"),
    ("n8n_password", "<N8N_DB_PASSWORD>"),
    ("change_this_password", "<CHANGE_THIS_PASSWORD>"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def workspace_root(repo: Path) -> Path:
    env_root = os.environ.get("INTERNAL_SERVICES_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return repo.parents[2]


def discover_runbooks(workspace: Path, repo: Path) -> list[Path]:
    runbooks: list[Path] = []
    for path in workspace.rglob("RUNBOOK*.md"):
        if repo in path.parents:
            continue
        if path.is_file():
            runbooks.append(path)
    return sorted(runbooks)


def public_topic_prefix(path: Path) -> str | None:
    for prefix in PUBLIC_TOPIC_PREFIXES:
        if path.name.startswith(prefix):
            return prefix
    return None


def public_runbooks(runbooks: list[Path]) -> list[Path]:
    return [path for path in runbooks if public_topic_prefix(path)]


def load_reverse_path_map(workspace: Path) -> list[tuple[str, str]]:
    index_path = workspace / "WORKSPACE_INDEX.md"
    lines = index_path.read_text().splitlines()
    in_table = False
    pairs: list[tuple[str, str]] = []

    for line in lines:
        if line.strip() == "## Old Path Map":
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] == "Old Root Path" or set(cells[0]) == {"-"}:
            continue
        old_path, new_path = (cell.strip("`") for cell in cells)
        pairs.append((new_path, old_path))

    return sorted(pairs, key=lambda item: len(item[0]), reverse=True)


def source_relative_path(
    src: Path,
    workspace: Path,
    reverse_map: list[tuple[str, str]],
) -> Path:
    rel = src.relative_to(workspace).as_posix()
    for new_prefix, old_prefix in reverse_map:
        if rel == new_prefix.rstrip("/"):
            return Path(old_prefix.rstrip("/"))
        if rel.startswith(new_prefix):
            suffix = rel[len(new_prefix) :]
            return Path(old_prefix + suffix)
    return Path(rel)


def reset_source_paths(source_paths: Path) -> None:
    if source_paths.exists():
        shutil.rmtree(source_paths)
    source_paths.mkdir(parents=True, exist_ok=True)


def sanitize_text(text: str) -> str:
    for old, new in SANITIZE_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def write_runbook_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    dest.write_text(sanitize_text(text))


def mirror_runbooks(
    runbooks: list[Path],
    workspace: Path,
    source_paths: Path,
    reverse_map: list[tuple[str, str]],
) -> None:
    for src in runbooks:
        dest = source_paths / source_relative_path(src, workspace, reverse_map)
        write_runbook_copy(src, dest)


def extract_date(path: Path) -> str | None:
    matches = DATE_RE.findall(path.name)
    if not matches:
        return None
    return matches[-1]


def current_public_runbooks(runbooks: list[Path]) -> list[Path]:
    selected_by_prefix: dict[str, Path] = {}

    for path in runbooks:
        prefix = public_topic_prefix(path)
        if not prefix:
            continue
        date_str = extract_date(path)
        if not date_str:
            continue
        current = selected_by_prefix.get(prefix)
        if current is None or (extract_date(current) or "") < date_str:
            selected_by_prefix[prefix] = path

    selected = [selected_by_prefix[prefix] for prefix in PUBLIC_TOPIC_PREFIXES if prefix in selected_by_prefix]
    if not selected:
        raise SystemExit("No current public runbooks matched the configured topic set.")
    return selected


def reset_root_runbooks(repo: Path, selected: list[Path]) -> None:
    for path in repo.glob("RUNBOOK*.md"):
        path.unlink()
    for src in selected:
        write_runbook_copy(src, repo / src.name)


def update_readme(repo: Path, selected: list[Path]) -> None:
    readme_path = repo / "README.md"
    readme = readme_path.read_text()
    start = readme.find(README_MARKER_START)
    end = readme.find(README_MARKER_END)
    if start == -1 or end == -1 or end < start:
        raise SystemExit("README markers for current runbooks were not found.")

    lines = [
        README_MARKER_START,
        "Currently published on the repo root:",
        "",
    ]
    for path in selected:
        lines.append(f"- [{path.name}]({path.name})")
    lines.extend(["", README_MARKER_END])
    replacement = "\n".join(lines)

    updated = readme[:start] + replacement + readme[end + len(README_MARKER_END) :]
    readme_path.write_text(updated)


def main() -> None:
    repo = repo_root()
    workspace = workspace_root(repo)
    source_paths = repo / "source_paths"

    runbooks = public_runbooks(discover_runbooks(workspace, repo))
    reverse_map = load_reverse_path_map(workspace)
    reset_source_paths(source_paths)
    mirror_runbooks(runbooks, workspace, source_paths, reverse_map)

    selected = current_public_runbooks(runbooks)
    reset_root_runbooks(repo, selected)
    update_readme(repo, selected)

    print(f"Mirrored {len(runbooks)} runbooks into {source_paths}")
    print(f"Promoted {len(selected)} current public runbooks to {repo}")


if __name__ == "__main__":
    main()
