from __future__ import annotations
from pathlib import Path
import sys
import argparse
import re
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

# Fixed project root
ROOT = Path("/Users/buddy/Desktop/projects/buddyowens-site").resolve()

# Output path
OUT_FILE = ROOT / "output" / "combined_files.txt"

# Limits
MAX_BYTES = 300_000
PREVIEW_BYTES = 4096
MAX_POSTS_LIST = 500

# Important files to preview
IMPORTANT_FILES = [
    "hugo.toml",
    "config/_default/menus.toml",
    "config/_default/outputs.toml",
    "content/about/_index.md",
    "content/search/_index.md",  # corrected
]

INCLUDE_PATTERNS = [
    ("CONFIG", [
        "hugo.toml", "hugo.yaml", "hugo.json",
        "config/**/*.*",
        "netlify.toml", "vercel.*",
        "README.md",
    ]),
    ("CI", [
        ".github/workflows/**/*.{yml,yaml}",
    ]),
    ("ARCHETYPES", [
        "archetypes/**/*.md",
    ]),
    ("LAYOUTS", [
        "layouts/**/*.*",
        "layouts/partials/**/*.*",
        "layouts/shortcodes/**/*.*",
    ]),
    ("CONTENT", [
        "content/**/*.md",
        "content/**/*.{toml,yaml,yml,json,csv,txt}",
        "content/**/*.{png,jpg,jpeg,webp,svg,gif}",
    ]),
    ("DATA", [
        "data/**/*.{toml,yaml,yml,json,csv}",
    ]),
    ("ASSETS", [
        "assets/**/*.{css,js,scss,ts}",
        "assets/**/*.{png,jpg,jpeg,webp,svg,gif}",
    ]),
    ("STATIC", [
        "static/**/*.{css,js,scss,ts}",
        "static/**/*.{png,jpg,jpeg,webp,svg,gif,ico}",
        "static/**/*.{txt,xml}",
        "static/**/*.html",
        "static/**/*.json",
    ]),
    ("DEV", [
        "dev/**/*.md",
        "dev/log.md",
    ]),
]

EXCLUDE_DIR_NAMES = {
    "public", "themes", "resources", "_gen", "node_modules",
    ".git", ".idea", ".vscode", "output",
}
EXCLUDE_NAME_SUBSTRINGS = {
    "apikey", "api_key", "secret", "credentials", ".env",
    "uni_geo_mapping.json", "unmatched_universities",
    ".bak",  # exclude backups
}
EXCLUDE_FILE_SUFFIXES = {
    ".lock", ".zip", ".tar", ".gz", ".map", ".bin", ".DS_Store",
}

def is_excluded(path: Path) -> bool:
    try:
        rel_parts = path.relative_to(ROOT).parts
    except ValueError:
        rel_parts = path.parts
    if any(part in EXCLUDE_DIR_NAMES for part in rel_parts):
        return True
    lower = path.name.lower()
    if any(sub in lower for sub in EXCLUDE_NAME_SUBSTRINGS):
        return True
    if any(str(path).endswith(suf) for suf in EXCLUDE_FILE_SUFFIXES):
        return True
    return False

FM_BOUNDARY = re.compile(r"^---\s*$|^\+\+\+\s*$")  # YAML or TOML style

def parse_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or not FM_BOUNDARY.match(lines[0].strip()):
        return {}, text
    sep = lines[0].strip()
    try:
        end_idx = next(i for i in range(1, len(lines)) if lines[i].strip() == sep)
    except StopIteration:
        return {}, text
    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx+1:])

    # Try JSON, then simple key: value
    try:
        fm = json.loads(fm_text)
        return fm if isinstance(fm, dict) else {}, body
    except Exception:
        pass

    fm: Dict[str, Any] = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if v.startswith("[") and v.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            fm[k] = items
        else:
            fm[k] = v
    return fm, body

def _fix_tz_colon(s: str) -> str:
    # turn 2025-09-07T02:05:29-0400 -> 2025-09-07T02:05:29-04:00
    m = re.search(r"([+-]\d{2})(\d{2})$", s)
    if m:
        return s[:m.start()] + f"{m.group(1)}:{m.group(2)}"
    return s

def parse_date(d: str | None) -> Optional[datetime]:
    if not d:
        return None
    s = str(d).strip().strip('"').strip("'")
    # RFC3339 with or without colon in offset
    for cand in (s, _fix_tz_colon(s)):
        try:
            return datetime.fromisoformat(cand.replace("Z", "+00:00"))
        except Exception:
            pass
    # bare date
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None

def gather_files():
    ordered_sections = []
    for header, patterns in INCLUDE_PATTERNS:
        files = []
        for pat in patterns:
            for p in ROOT.glob(pat):
                if p.is_file() and not is_excluded(p):
                    files.append(p)
        files = sorted(set(files), key=lambda x: str(x).lower())
        ordered_sections.append((header, files))
    return ordered_sections

def list_posts_index() -> Tuple[int, list, int, int]:
    """
    Returns (count, rows, published_count, draft_count)
    rows: (rel_path, title, date_str, draft_str, tags)
    Sorted by parsed date desc (fallback mtime desc).
    """
    posts_root = ROOT / "content" / "posts"
    rows = []
    if not posts_root.exists():
        return 0, rows, 0, 0

    for bundle in sorted(posts_root.glob("*")):
        if not bundle.is_dir():
            continue
        idx = bundle / "index.md"
        if not idx.exists() or is_excluded(idx):
            continue
        rel = idx.relative_to(ROOT)
        try:
            text = idx.read_text(encoding="utf-8")
        except Exception:
            rows.append((str(rel), "", "", "", [], None, idx.stat().st_mtime))
            continue
        fm, _ = parse_front_matter(text)
        title = str(fm.get("title", "")).strip()
        date_str = str(fm.get("date", "")).strip()
        draft_raw = str(fm.get("draft", "")).strip().lower()
        draft_flag = draft_raw in {"true", "yes", "1"}
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        dt = parse_date(date_str)
        rows.append((str(rel), title, date_str, str(draft_flag).lower(), tags, dt, idx.stat().st_mtime))

    # sort by dt desc; fallback to mtime desc
    rows.sort(key=lambda r: (r[5] if r[5] else datetime.fromtimestamp(r[6])), reverse=True)

    published = sum(1 for r in rows if r[3] == "false")
    drafts = len(rows) - published

    # trim metadata before printing
    trimmed = [(r[0], r[1], r[2], r[3], r[4]) for r in rows[:MAX_POSTS_LIST]]
    return len(rows), trimmed, published, drafts

def write_summary(out):
    out.write("# === SUMMARY ===\n\n")
    out.write(f"Root: {ROOT}\n\n")

    count, rows, published, drafts = list_posts_index()
    out.write(f"## Posts ({count})  —  Published: {published}  Drafts: {drafts}\n\n")
    if not rows:
        out.write("[none]\n\n")
    else:
        for rel, title, date, draft, tags in rows:
            tags_str = f" tags={tags}" if tags else ""
            draft_str = f" draft={draft}" if draft != "" else ""
            out.write(f"- {rel}  —  title='{title}'  date='{date}'{draft_str}{tags_str}\n")
        out.write("\n")

    out.write("## Important Files (previews)\n\n")
    for rel in IMPORTANT_FILES:
        p = ROOT / rel
        if not p.exists() or not p.is_file() or is_excluded(p):
            continue
        out.write(f"### {rel}\n\n")
        try:
            b = p.read_bytes()
            preview = b[:PREVIEW_BYTES].decode("utf-8", errors="replace")
            out.write("```text\n")
            out.write(preview)
            if len(b) > PREVIEW_BYTES:
                out.write("\n[...trimmed preview...]\n")
            out.write("\n```\n\n")
        except Exception as e:
            out.write(f"[unreadable: {e}]\n\n")

def write_sections(out, sections, paths_only: bool):
    for header, files in sections:
        out.write(f"# --- {header} ---\n\n")
        if not files:
            out.write("# [none]\n\n")
            continue
        for fp in files:
            rel = fp.relative_to(ROOT)
            out.write(f"# {rel}\n\n")
            if paths_only:
                continue
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

def write_combined(sections, paths_only: bool, summary_only: bool):
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as out:
        out.write("# Combined site files for review\n\n")
        write_summary(out)
        if summary_only:
            out.write("\n# [End: summary only]\n")
            print(f"Wrote {OUT_FILE}")
            return
        out.write("\n")
        write_sections(out, sections, paths_only=paths_only)
    print(f"Wrote {OUT_FILE}")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Combine key Hugo site files into one review doc.")
    parser.add_argument("--paths-only", action="store_true",
                        help="Only list file paths for sections (previews still shown for important files).")
    parser.add_argument("--summary-only", action="store_true",
                        help="Write only the summary (posts index + important file previews).")
    args = parser.parse_args(argv)

    sections = gather_files()
    write_combined(sections, paths_only=args.paths_only, summary_only=args.summary_only)

if __name__ == "__main__":
    sys.exit(main())