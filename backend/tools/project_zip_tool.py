from __future__ import annotations

import base64
import io
import zipfile


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".env",
    ".md",
    ".txt",
    ".log",
    ".sql",
    ".html",
    ".css",
    ".sh",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
}

SKIP_PARTS = {
    "__pycache__",
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    ".next",
    ".vite",
}

MAX_ZIP_BYTES = 2_500_000
MAX_FILES = 18
MAX_FILE_BYTES = 80_000
MAX_SNIPPET_CHARS = 1_200


def _is_safe_text_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return False
    parts = set(normalized.split("/"))
    if parts & SKIP_PARTS:
        return False
    suffix = "." + normalized.rsplit(".", 1)[-1].lower() if "." in normalized else ""
    return suffix in TEXT_EXTENSIONS


def summarize_project_zip(zip_base64: str | None, filename: str | None = None) -> dict[str, object]:
    if not zip_base64:
        return {"context": "", "summary": "No project zip supplied.", "files": []}

    try:
        raw = base64.b64decode(zip_base64, validate=True)
    except Exception:
        return {"context": "", "summary": "Project zip could not be decoded.", "files": []}

    if len(raw) > MAX_ZIP_BYTES:
        return {
            "context": "",
            "summary": f"Project zip was skipped because it exceeded {MAX_ZIP_BYTES // 1_000_000} MB.",
            "files": [],
        }

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return {"context": "", "summary": "Uploaded project file was not a valid zip archive.", "files": []}

    selected: list[dict[str, str]] = []
    skipped = 0
    for info in archive.infolist():
        if info.is_dir() or not _is_safe_text_path(info.filename) or info.file_size > MAX_FILE_BYTES:
            skipped += 1
            continue
        try:
            content = archive.read(info.filename).decode("utf-8", errors="replace")
        except Exception:
            skipped += 1
            continue
        selected.append({"path": info.filename, "snippet": content[:MAX_SNIPPET_CHARS]})
        if len(selected) >= MAX_FILES:
            break

    if not selected:
        return {
            "context": "",
            "summary": "Project zip was read, but no supported text files were selected.",
            "files": [],
        }

    zip_label = filename or "uploaded project zip"
    lines = [f"Project context from {zip_label}:"]
    for item in selected:
        lines.append(f"\n--- FILE: {item['path']} ---\n{item['snippet']}")
    summary = f"Included {len(selected)} text file(s) from project zip"
    if skipped:
        summary += f"; skipped {skipped} unsupported, large, or unsafe item(s)"
    return {"context": "\n".join(lines), "summary": summary + ".", "files": [item["path"] for item in selected]}
