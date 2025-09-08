from __future__ import annotations
from pathlib import Path
import sys
import fnmatch
import subprocess
import time

# ---- tweakable settings (no CLI) ----
MAX_TOTAL_BYTES = 80_000
MAX_PER_FILE_BYTES = 12_000
GIT_SINCE_DAYS = 540               # only include files changed in this window if git info is available
USE_GIT = True                     # auto-filters to tracked + recently-changed files when possible
ROOT_MARKERS = {"hugo.toml", ".git"}

# include only what you typically hand-edit for Hugo sites
INCLUDE_GLOBS = [
    "hugo.toml", "config.*", "netlify.toml", "vercel.json",
    "package.json", "pnpm-lock.yaml", "package-lock.json", "yarn.lock",
    "postcss.config.*", "tailwind.config.*", "tsconfig.*", ".nvmrc",
    "content/**/*.md", "content/**/_index.md",
    "layouts/**/*.html", "layouts/**/*.xml", "layouts/**/*.tmpl",
    "layouts/**/*.md", "layouts/partials/**/*", "layouts/shortcodes/**/*",
    "assets/**/*.[sc]css", "assets/**/*.[jt]s", "assets/**/*.[jt]sx", "assets/**/*.ts",
    "static/**/*.css", "static/**/*.js",
    "data/**/*.yaml", "data/**/*.yml", "data/**/*.toml", "data/**/*.json",
    "archetypes/**/*",
]

# never include these dirs
EXCLUDE_DIRS = {
    "public", "resources", "_gen", "node_modules", ".git", ".idea",
    ".vscode", "output", ".cache", "dist", "build", "__pycache__", "themes",
}

# optionally allow your custom theme if you truly edit it
OPTIONAL_THEME_DIRS = set()  # e.g., {"themes/my-custom-theme"}
# -------------------------------------

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
    # permit explicitly whitelisted theme dirs
    if "themes" in rel_parts and not any(str(path).startswith(str(root / d)) for d in OPTIONAL_THEME_DIRS):
        return True
    if any(part in EXCLUDE_DIRS for part in rel_parts):
        return True
    return False

def matches_any_glob(p: Path, root: Path) -> bool:
    rel = str(p.relative_to(root))
    for pattern in INCLUDE_GLOBS:
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False

def git_tracked_recent(root: Path) -> set[str]:
    if not USE_GIT or not (root / ".git").exists():
        return set()
    try:
        # tracked files
        tracked = subprocess.check_output(
            ["git", "-C", str(root), "ls-files"], text=True
        ).splitlines()

        # recently changed files
        since = f"{GIT_SINCE_DAYS}.days"
        recent = subprocess.check_output(
            ["git", "-C", str(root), "log", f"--since={since}", "--name-only", "--pretty=format:"],
            text=True
        ).splitlines()

        # staged or unstaged changes right now
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True
        ).splitlines()
        status_files = [line[3:] for line in status if len(line) > 3]

        return set(filter(None, tracked + recent + status_files))
    except Exception:
        return set()

def priority_key(p: Path, root: Path) -> tuple[int, str]:
    rel = str(p.relative_to(root))
    # simple tiering
    tiers = [
        ("hugo.toml", 0),
        ("config.", 0),
        ("layouts/", 1),
        ("layouts/partials/", 0),
        ("layouts/shortcodes/", 0),
        ("content/", 2),
        ("assets/", 3),
        ("static/", 4),
        ("data/", 5),
        ("archetypes/", 6),
        ("package.json", 1),
        ("tailwind.config", 1),
        ("postcss.config", 1),
    ]
    for prefix, t in tiers:
        if rel.startswith(prefix):
            return (t, rel.lower())
    return (9, rel.lower())

def code_fence_lang(suffix: str) -> str:
    m = {
        ".py": "python", ".js": "javascript", ".ts": "ts", ".tsx": "tsx", ".jsx": "jsx",
        ".css": "css", ".scss": "scss", ".html": "html", ".xml": "xml",
        ".md": "markdown", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml", ".json": "json",
        ".sh": "bash", ".zsh": "bash", ".bash": "bash",
    }
    return m.get(suffix.lower(), "")

def candidate_files(root: Path) -> list[Path]:
    tracked_recent = git_tracked_recent(root)
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if is_excluded(p, root):
            continue
        if not matches_any_glob(p, root):
            continue
        if tracked_recent:
            rel = str(p.relative_to(root))
            if rel not in tracked_recent:
                continue
        files.append(p)
    files.sort(key=lambda x: priority_key(x, root))
    return files

def read_trimmed(fp: Path) -> str:
    try:
        raw = fp.read_bytes()
    except Exception:
        return "[unreadable]\n"
    if len(raw) <= MAX_PER_FILE_BYTES:
        return raw.decode("utf-8", errors="replace")
    # keep head and tail with a small divider
    head = raw[: MAX_PER_FILE_BYTES // 2]
    tail = raw[-MAX_PER_FILE_BYTES // 2 :]
    return head.decode("utf-8", errors="replace") + "\n# … trimmed …\n" + tail.decode("utf-8", errors="replace")

def write_combined(root: Path, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with out_file.open("w", encoding="utf-8") as out:
        out.write("# Important Hugo files\n\n")
        out.write(f"Root: {root}\n\n")
        for fp in candidate_files(root):
            rel = fp.relative_to(root)
            fence_lang = code_fence_lang(fp.suffix)
            header = f"# {rel}\n\n"
            open_fence = f"```{fence_lang}\n" if fence_lang else "```\n"
            block_body = read_trimmed(fp)
            block = header + open_fence + block_body + "\n```\n\n"
            b = len(block.encode("utf-8"))
            if total + b > MAX_TOTAL_BYTES:
                break
            out.write(block)
            total += b
    print(f"Wrote {out_file} ({total} bytes)")

def main() -> int:
    root = find_repo_root(Path.cwd())
    out_file = root / "output" / "important_hugo_files.txt"
    write_combined(root, out_file)
    return 0

if __name__ == "__main__":
    sys.exit(main())