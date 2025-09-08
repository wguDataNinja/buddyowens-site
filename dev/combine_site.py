from __future__ import annotations
from pathlib import Path
import sys

# Fixed project root
ROOT = Path("/Users/buddy/Desktop/projects/buddyowens-site").resolve()

# Output path
OUT_FILE = ROOT / "output" / "combined_files.txt"

# Max bytes to read per file
MAX_BYTES = 300_000

INCLUDE_PATTERNS = [
    ("CONFIG", ["hugo.toml", "hugo.yaml", "hugo.json", "config/**/*.*",
                "netlify.toml", "vercel.*", "README.md"]),
    ("CI", [".github/workflows/**/*.{yml,yaml}"]),
    ("ARCHETYPES", ["archetypes/**/*.md"]),
    ("LAYOUTS", ["layouts/**/*.*", "layouts/partials/**/*.*", "layouts/shortcodes/**/*.*"]),
    ("CONTENT", ["content/**/*.md", "content/**/*.{toml,yaml,yml,json,csv,txt}",
                 "content/**/*.{png,jpg,jpeg,webp,svg,gif}"]),
    ("DATA", ["data/**/*.{toml,yaml,yml,json,csv}"]),
    ("ASSETS", ["assets/**/*.{css,js,scss,ts}", "assets/**/*.{png,jpg,jpeg,webp,svg,gif}"]),
    ("STATIC", ["static/**/*.{css,js,scss,ts}", "static/**/*.{png,jpg,jpeg,webp,svg,gif,ico}",
                "static/**/*.{txt,xml}", "static/**/*.html", "static/**/*.json"]),
    ("DEV", ["dev/**/*.md", "dev/log.md"]),
]

EXCLUDE_DIR_NAMES = {"public", "themes", "resources", "_gen", "node_modules",
                     ".git", ".idea", ".vscode", "output"}
EXCLUDE_NAME_SUBSTRINGS = {"apikey", "api_key", "secret", "credentials", ".env",
                           "uni_geo_mapping.json", "unmatched_universities"}
EXCLUDE_FILE_SUFFIXES = {".lock", ".zip", ".tar", ".gz", ".map", ".bin", ".DS_Store"}


def is_excluded(path: Path) -> bool:
    # exclude by dir
    if any(part in EXCLUDE_DIR_NAMES for part in path.relative_to(ROOT).parts):
        return True
    # exclude by name
    lower = path.name.lower()
    if any(sub in lower for sub in EXCLUDE_NAME_SUBSTRINGS):
        return True
    if any(str(path).endswith(suf) for suf in EXCLUDE_FILE_SUFFIXES):
        return True
    return False


def gather_files():
    ordered_sections = []
    for header, patterns in INCLUDE_PATTERNS:
        files = []
        for pat in patterns:
            for p in ROOT.glob(pat):
                if p.is_file() and not is_excluded(p):
                    files.append(p)
        files = sorted(set(files), key=lambda x: str(x).lower())
        if files:
            ordered_sections.append((header, files))
    return ordered_sections


def write_combined(sections):
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as out:
        out.write("# Combined site files for review\n\n")
        out.write(f"# Root: {ROOT}\n\n")
        for header, files in sections:
            out.write(f"# --- {header} ---\n\n")
            for fp in files:
                rel = fp.relative_to(ROOT)
                out.write(f"# {rel}\n\n")
                try:
                    size = fp.stat().st_size
                    if size > MAX_BYTES:
                        out.write(f"# [skipped: file too large ({size} bytes)]\n\n")
                        continue
                    text = fp.read_text(encoding="utf-8")
                    out.write(text)
                except UnicodeDecodeError:
                    out.write("# [skipped: non-text or unreadable]\n")
                out.write("\n\n")
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    sections = gather_files()
    write_combined(sections)