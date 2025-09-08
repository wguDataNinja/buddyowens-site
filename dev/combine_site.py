from __future__ import annotations
from pathlib import Path
import sys
import re

# ---- settings you can tweak at top (no CLI) ----
MAX_TOTAL_BYTES = 300_000
ROOT_MARKERS = {"hugo.toml", ".git"}
EXCLUDE_DIRS = {"public", "themes", "resources", "_gen", "node_modules", ".git", ".idea", ".vscode", "output", ".cache", "dist", "build", "__pycache__"}
EXCLUDE_NAME_SUBSTRINGS = {"apikey", "api_key", "secret", "credentials", ".env", ".lock", ".DS_Store", ".bak"}
ALLOW_EXTS = {
    ".md", ".markdown", ".txt",
    ".toml", ".yaml", ".yml", ".json", ".csv", ".ini", ".env.example",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".scss", ".html",
    ".go", ".rs", ".java", ".kt", ".c", ".cpp", ".h", ".hpp",
    ".sh", ".bash", ".zsh", ".ps1", ".rb", ".php",
}
# -------------------------------------------------

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if any((cur / m).exists() for m in ROOT_MARKERS):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()

def is_excluded(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    if any(part in EXCLUDE_DIRS for part in rel_parts):
        return True
    low = path.name.lower()
    if any(s in low for s in EXCLUDE_NAME_SUBSTRINGS):
        return True
    return False

def looks_textual(p: Path) -> bool:
    # allow by extension first
    if p.suffix.lower() in ALLOW_EXTS:
        return True
    # quick binary sniff as fallback
    try:
        with p.open("rb") as fh:
            chunk = fh.read(1024)
        if b"\x00" in chunk:
            return False
        # if mostly printable, accept
        txt = chunk.decode("utf-8", errors="ignore")
        printable = sum(ch.isprintable() or ch in "\r\n\t" for ch in txt)
        return printable >= max(1, len(txt) * 0.9)
    except Exception:
        return False

def code_fence_lang(suffix: str) -> str:
    m = {
        ".py": "python", ".js": "javascript", ".ts": "ts", ".tsx": "tsx", ".jsx": "jsx",
        ".css": "css", ".scss": "scss", ".html": "html",
        ".md": "markdown", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml", ".json": "json",
        ".sh": "bash", ".zsh": "bash", ".bash": "bash", ".ps1": "powershell",
        ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
        ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
        ".rb": "ruby", ".php": "php", ".ini": "ini", ".csv": "csv", ".txt": "text",
    }
    return m.get(suffix.lower(), "")

def gather_files(root: Path) -> list[Path]:
    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if is_excluded(p, root):
            continue
        if not looks_textual(p):
            continue
        files.append(p)
    # stable sort by path
    files.sort(key=lambda x: str(x).lower())
    return files

def write_combined(root: Path, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with out_file.open("w", encoding="utf-8") as out:
        out.write("# Combined project files\n\n")
        out.write(f"Root: {root}\n\n")
        for fp in gather_files(root):
            rel = fp.relative_to(root)
            header = f"# {rel}\n\n"
            fence_lang = code_fence_lang(fp.suffix)
            open_fence = f"```{fence_lang}\n" if fence_lang else "```\n"
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = "[unreadable]\n"
            block = header + open_fence + text + "\n```\n\n"
            b = len(block.encode("utf-8"))
            if total + b > MAX_TOTAL_BYTES:
                remaining = MAX_TOTAL_BYTES - total
                if remaining > 0:
                    # write a trimmed tail to hit the cap cleanly
                    trimmed = block.encode("utf-8")[:remaining].decode("utf-8", errors="ignore")
                    out.write(trimmed)
                    total += len(trimmed.encode("utf-8"))
                out.write("\n# [truncated: size cap reached]\n")
                break
            out.write(block)
            total += b
    print(f"Wrote {out_file} ({total} bytes)")

def main() -> int:
    root = find_repo_root(Path.cwd())
    out_file = root / "output" / "combined_files.txt"
    write_combined(root, out_file)
    return 0

if __name__ == "__main__":
    sys.exit(main())