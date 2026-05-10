import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "backend" / "src",
    ROOT / "frontend" / "src",
]
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}
EXTS = {".py", ".ts", ".tsx", ".js"}

PATTERNS = [
    re.compile(r"\bTODO\b"),
    re.compile(r"\bFIXME\b"),
    re.compile(r"\bXXX\b"),
    re.compile(r"\bHACK\b"),
    re.compile(r"NotImplementedError"),
]


def scan_file(path: Path) -> list[tuple[int, str]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        for p in PATTERNS:
            if p.search(line):
                hits.append((i, line.strip()))
                break
    return hits


def main() -> int:
    findings: list[tuple[Path, int, str]] = []
    for root in TARGETS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
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
