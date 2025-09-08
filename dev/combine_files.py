from __future__ import annotations
from pathlib import Path
import sys
import fnmatch
import subprocess

# ---- tweakable settings (no CLI) ----
MAX_TOTAL_BYTES = 80_000
MAX_PER_FILE_BYTES = 12_000
GIT_SINCE_DAYS = 540
USE_GIT = True
ROOT_MARKERS = {"hugo.toml", ".git"}

# include typical hand-edited Hugo files + map assets
INCLUDE_GLOBS = [
    # config
    "hugo.toml", "config.*", "netlify.toml", "vercel.json",

    # package/build (optional but useful)
    "package.json", "pnpm-lock.yaml", "package-lock.json", "yarn.lock",
    "postcss.config.*", "tailwind.config.*", "tsconfig.*", ".nvmrc",

    # site content and layouts
    "content/**/*.md", "content/**/_index.md",
    "layouts/**/*.html", "layouts/**/*.xml", "layouts/**/*.tmpl",
    "layouts/**/*.md", "layouts/partials/**/*", "layouts/shortcodes/**/*",

    # assets (css/js/ts)
    "assets/**/*.[sc]css", "assets/**/*.[jt]s", "assets/**/*.[jt]sx", "assets/**/*.ts",

    # static assets (include html so maps show up; include css/js/images for Folium/Plotly)
    "static/**/*.html",
    "static/**/*.css", "static/**/*.js",
    "static/**/*.png", "static/**/*.jpg", "static/**/*.jpeg", "static/**/*.svg",
    "static/**/*.json", "static/**/*.geojson",

    # data and archetypes
    "data/**/*.yaml", "data/**/*.yml", "data/**/*.toml", "data/**/*.json",
    "archetypes/**/*",
]

# never include these dirs
EXCLUDE_DIRS = {
    "public", "resources", "_gen", "node_modules", ".git", ".idea",
    ".vscode", "output", ".cache", "dist", "build", "__pycache__", "themes",
}

# allow explicit theme dirs if you actually edit them
OPTIONAL_THEME_DIRS: set[str] = set()
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
        tracked = subprocess.check_output(
            ["git", "-C", str(root), "ls-files"], text=True
        ).splitlines()
        since = f"{GIT_SINCE_DAYS}.days"
        recent = subprocess.check_output(
            ["git", "-C", str(root), "log", f"--since={since}", "--name-only", "--pretty=format:"],
            text=True
        ).splitlines()
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True
        ).splitlines()
        status_files = [line[3:] for line in status if len(line) > 3]
        return set(filter(None, tracked + recent + status_files))
    except Exception:
        return set()

def priority_key(p: Path, root: Path) -> tuple[int, str]:
    """Lower tier number = higher priority in the combined output."""
    rel = str(p.relative_to(root))
    # Boost maps so you can spot issues fast
    if rel.startswith("static/maps/"):
        return (0, rel.lower())
    tiers = [
        ("hugo.toml", 1),
        ("config.", 1),
        ("layouts/partials/", 2),
        ("layouts/shortcodes/", 2),
        ("layouts/", 3),
        ("content/", 4),
        ("assets/", 5),
        ("static/", 6),
        ("data/", 7),
        ("archetypes/", 8),
        ("package.json", 3),
        ("tailwind.config", 3),
        ("postcss.config", 3),
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

def read_trimmed(fp: Path) -> str:
    try:
        raw = fp.read_bytes()
    except Exception:
        return "[unreadable]\n"
    if len(raw) <= MAX_PER_FILE_BYTES:
        return raw.decode("utf-8", errors="replace")
    head = raw[: MAX_PER_FILE_BYTES // 2]
    tail = raw[-MAX_PER_FILE_BYTES // 2 :]
    return head.decode("utf-8", errors="replace") + "\n# … trimmed …\n" + tail.decode("utf-8", errors="replace")

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