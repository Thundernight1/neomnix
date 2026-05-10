import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    "tests",
    "e2e",
}
SKIP_FILES = {
    "secrets.env",
    "secrets.env.example",
    ".env",
    ".env.example",
}
EXTS = {".py", ".yml", ".yaml", ".json", ".ts", ".tsx", ".js", ".md", ".sh", ".ini"}

PATTERNS = [
    re.compile(r"sk_live_[0-9A-Za-z]{10,}"),
    re.compile(r"pk_live_[0-9A-Za-z]{10,}"),
    re.compile(r"whsec_[0-9A-Za-z]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key|token|password)\b\s*=\s*['\"][^'\"]{8,}['\"]"),
]


def should_skip_path(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return True
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    return False


def scan_file(path: Path) -> list[tuple[int, str]]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

    hits: list[tuple[int, str]] = []
    for i, line in enumerate(content, start=1):
        for p in PATTERNS:
            if p.search(line):
                hits.append((i, line.strip()))
                break
    return hits


def main() -> int:
    findings: list[tuple[Path, int, str]] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if should_skip_path(p):
                continue
            if p.suffix.lower() not in EXTS:
                continue
            for line_no, line in scan_file(p):
                findings.append((p, line_no, line))

    if not findings:
        return 0

    for p, line_no, line in findings:
        rel = p.relative_to(ROOT)
        print(f"{rel}:{line_no}: {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
