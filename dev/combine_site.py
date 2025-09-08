from __future__ import annotations
from pathlib import Path
import sys
import argparse
import re
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

# ==== REPO ROOT DETECTION ====
def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if (cur / "hugo.toml").exists() or (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()

# default: use script dir or cwd; can override with --root
DEFAULT_ROOT = find_repo_root(Path(__file__).parent if "__file__" in globals() else Path.cwd())

# Output path
def default_out_file(root: Path) -> Path:
    return root / "output" / "combined_files.txt"

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
    "content/search/_index.md",
    "layouts/partials/google_analytics.html",
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
    "uni_geo_mapping.json", "unmatched_universities", ".bak",
}
EXCLUDE_FILE_SUFFIXES = {
    ".lock", ".zip", ".tar", ".gz", ".map", ".bin", ".DS_Store",
}

def is_excluded(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
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
    m = re.search(r"([+-]\d{2})(\d{2})$", s)
    if m:
        return s[:m.start()] + f"{m.group(1)}:{m.group(2)}"
    return s

def parse_date(d: str | None) -> Optional[datetime]:
    if not d:
        return None
    s = str(d).strip().strip('"').strip("'")
    for cand in (s, _fix_tz_colon(s)):
        try:
            return datetime.fromisoformat(cand.replace("Z", "+00:00"))
        except Exception:
            pass
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None

def gather_files(root: Path):
    ordered_sections = []
    for header, patterns in INCLUDE_PATTERNS:
        files = []
        for pat in patterns:
            for p in root.glob(pat):
                if p.is_file() and not is_excluded(p, root):
                    files.append(p)
        files = sorted(set(files), key=lambda x: str(x).lower())
        ordered_sections.append((header, files))
    return ordered_sections

# ===== CI DIAGNOSTICS =====

def read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""

def check_hugo_workflows(root: Path) -> list[str]:
    """Inspect .github/workflows for Hugo setup and version."""
    msgs = []
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.exists():
        msgs.append("FAIL: .github/workflows missing")
        return msgs

    wfs = [p for p in wf_dir.glob("*.*") if p.suffix in {".yml", ".yaml"}]
    if not wfs:
        msgs.append("FAIL: no workflow files found")
        return msgs
    msgs.append(f"INFO: workflows found: {[p.name for p in wfs]}")

    pinned_ok = False
    any_manual = False
    any_setup = False
    wrong_versions = []

    for wf in wfs:
        t = read_text_safe(wf)

        # detect manual install step
        if re.search(r"hugo_extended_\d+\.\d+\.\d+_Linux-64bit\.tar\.gz", t):
            any_manual = True
            ver = re.search(r"hugo_extended_(\d+\.\d+\.\d+)_Linux-64bit\.tar\.gz", t)
            if ver and ver.group(1) == "0.149.1":
                pinned_ok = True
            elif ver:
                wrong_versions.append(f"{wf.name}: manual {ver.group(1)}")

        # detect actions/setup-hugo usage
        if "actions/setup-hugo@v" in t:
            any_setup = True
            m = re.search(r"hugo-version:\s*\"?([0-9.]+)\"?", t)
            if m:
                if m.group(1) == "0.149.1":
                    pinned_ok = True
                else:
                    wrong_versions.append(f"{wf.name}: setup-hugo {m.group(1)}")

        # detect peaceiris/actions-hugo (older)
        if "peaceiris/actions-hugo@v" in t and "hugo-version:" in t:
            m2 = re.search(r"hugo-version:\s*\"?([0-9.]+)\"?", t)
            if m2:
                if m2.group(1) == "0.149.1":
                    pinned_ok = True
                else:
                    wrong_versions.append(f"{wf.name}: peaceiris {m2.group(1)}")

    if len(wfs) > 1:
        msgs.append("WARN: multiple workflows present; ensure only one builds the site")

    if pinned_ok:
        msgs.append("PASS: Hugo pinned to 0.149.1 in workflows")
    else:
        msgs.append("FAIL: Hugo not pinned to 0.149.1 (PaperMod needs >=0.146); " +
                    ("manual install found " if any_manual else "") +
                    ("setup-hugo found " if any_setup else "") +
                    (f"| versions: {wrong_versions}" if wrong_versions else ""))

    return msgs

def check_submodule(root: Path) -> list[str]:
    msgs = []
    gm = root / ".gitmodules"
    if not gm.exists():
        return ["FAIL: .gitmodules not found (PaperMod submodule missing)"]

    txt = read_text_safe(gm)
    url_match = re.search(r'url\s*=\s*(\S+)', txt)
    url = url_match.group(1) if url_match else ""
    if not url:
        msgs.append("FAIL: PaperMod submodule URL not found in .gitmodules")
    else:
        if not url.endswith(".git"):
            msgs.append(f"FAIL: submodule URL missing .git suffix: {url}")
        if not url.startswith("https://"):
            msgs.append(f"WARN: prefer HTTPS URL: {url}")
        if "adityatelange/hugo-PaperMod" not in url:
            msgs.append(f"WARN: unexpected submodule repo: {url}")
        else:
            msgs.append(f"PASS: submodule URL OK: {url}")

    theme_dir = root / "themes" / "PaperMod"
    if not theme_dir.exists():
        msgs.append("FAIL: themes/PaperMod directory missing")
    else:
        git_dir = theme_dir / ".git"
        if git_dir.exists() or (theme_dir / ".gitmodules").exists():
            msgs.append("PASS: themes/PaperMod present (git metadata detected)")
        else:
            msgs.append("WARN: themes/PaperMod present but may not be an initialized submodule")

    return msgs

def check_ga_partial(root: Path) -> list[str]:
    p = root / "layouts" / "partials" / "google_analytics.html"
    if p.exists():
        return ["PASS: GA placeholder exists at layouts/partials/google_analytics.html"]
    else:
        return ["WARN: GA partial missing; add empty layouts/partials/google_analytics.html to silence theme error"]

# tiny toml-like parser to get simple keys and booleans
SIMPLE_KV_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*=\s*"(.*)"\s*$')
SIMPLE_BOOL_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*=\s*(true|false)\s*$', re.I)
SIMPLE_INT_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*=\s*([0-9]+)\s*$')

def parse_toml_like(text: str) -> dict:
    cfg = {}
    current_table = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            table = line.strip("[]").strip()
            current_table = [p.strip() for p in table.split(".") if p.strip()]
            continue
        m = SIMPLE_KV_RE.match(line)
        if m:
            key = ".".join(current_table + [m.group(1)]) if current_table else m.group(1)
            cfg[key] = m.group(2)
            continue
        m2 = SIMPLE_BOOL_RE.match(line)
        if m2:
            key = ".".join(current_table + [m2.group(1)]) if current_table else m2.group(1)
            cfg[key] = m2.group(2).lower() == "true"
            continue
        m3 = SIMPLE_INT_RE.match(line)
        if m3:
            key = ".".join(current_table + [m3.group(1)]) if current_table else m3.group(1)
            cfg[key] = int(m3.group(2))
            continue
    return cfg

def check_hugo_toml(root: Path) -> list[str]:
    msgs = []
    ht = root / "hugo.toml"
    if not ht.exists():
        return ["FAIL: hugo.toml not found at repo root"]

    raw = read_text_safe(ht)
    cfg = parse_toml_like(raw)

    base = str(cfg.get("baseURL", ""))
    theme = str(cfg.get("theme", ""))

    expected_base = "https://wguDataNinja.github.io/buddyowens-site/"

    if base == expected_base:
        msgs.append("PASS: baseURL set for GitHub Pages with correct casing")
    else:
        msgs.append(f"WARN: baseURL is '{base}' (expected '{expected_base}')")

    if theme == "PaperMod":
        msgs.append("PASS: theme = PaperMod")
    else:
        msgs.append(f"FAIL: theme not set to PaperMod (got '{theme}')")

    # URL flags that often break Pages
    rel = cfg.get("relativeURLs", None)
    can = cfg.get("canonifyURLs", None)
    if rel is True or can is True:
        flags = []
        if rel is True: flags.append("relativeURLs=true")
        if can is True: flags.append("canonifyURLs=true")
        msgs.append(f"WARN: {' and '.join(flags)} may break asset paths on GitHub Pages; suggest removing")
    else:
        msgs.append("PASS: no URL overrides detected (good)")

    # Pagination checks for Hugo >= 0.128
    # 1) deprecated key present?
    if re.search(r'^\s*paginate\s*=\s*\d+\s*$', raw, re.M):
        msgs.append("FAIL: deprecated 'paginate' key found; replace with [pagination] pagerSize = N")
    # 2) modern key present?
    pager_size = cfg.get("pagination.pagerSize", None)
    if pager_size is not None:
        msgs.append(f"PASS: pagination.pagerSize = {pager_size}")
    else:
        msgs.append("WARN: pagination.pagerSize not set; default may apply")

    return msgs

# ===== Existing site summary helpers =====

def list_posts_index(root: Path) -> Tuple[int, list, int, int]:
    posts_root = root / "content" / "posts"
    rows = []
    if not posts_root.exists():
        return 0, rows, 0, 0

    for bundle in sorted(posts_root.glob("*")):
        if not bundle.is_dir():
            continue
        idx = bundle / "index.md"
        if not idx.exists() or is_excluded(idx, root):
            continue
        rel = idx.relative_to(root)
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

    rows.sort(key=lambda r: (r[5] if r[5] else datetime.fromtimestamp(r[6])), reverse=True)
    published = sum(1 for r in rows if r[3] == "false")
    drafts = len(rows) - published
    trimmed = [(r[0], r[1], r[2], r[3], r[4]) for r in rows[:MAX_POSTS_LIST]]
    return len(rows), trimmed, published, drafts

def write_summary(out, root: Path):
    out.write("# === SUMMARY ===\n\n")
    out.write(f"Root: {root}\n\n")

    count, rows, published, drafts = list_posts_index(root)
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
        p = root / rel
        if not p.exists() or not p.is_file() or is_excluded(p, root):
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

def write_ci_checks(out, root: Path):
    out.write("## CI CHECKS\n\n")
    for line in check_hugo_workflows(root):
        out.write(f"{line}\n")
    for line in check_submodule(root):
        out.write(f"{line}\n")
    for line in check_ga_partial(root):
        out.write(f"{line}\n")
    for line in check_hugo_toml(root):
        out.write(f"{line}\n")
    out.write("\n")

def write_sections(out, sections, root: Path, paths_only: bool):
    for header, files in sections:
        out.write(f"# --- {header} ---\n\n")
        if not files:
            out.write("# [none]\n\n")
            continue
        for fp in files:
            rel = fp.relative_to(root)
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

def write_combined(root: Path, out_file: Path, sections, paths_only: bool, summary_only: bool):
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as out:
        out.write("# Combined site files for review\n\n")
        write_summary(out, root)
        write_ci_checks(out, root)
        if summary_only:
            out.write("\n# [End: summary only]\n")
            print(f"Wrote {out_file}")
            return
        out.write("\n")
        write_sections(out, sections, root=root, paths_only=paths_only)
    print(f"Wrote {out_file}")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Combine key Hugo site files into one review doc + CI checks.")
    parser.add_argument("--root", type=str, default=str(DEFAULT_ROOT),
                        help="Path to the repository root (defaults to auto-detected).")
    parser.add_argument("--out", type=str, default=None,
                        help="Output file path (defaults to <root>/output/combined_files.txt).")
    parser.add_argument("--paths-only", action="store_true",
                        help="Only list file paths for sections (previews still shown for important files).")
    parser.add_argument("--summary-only", action="store_true",
                        help="Write only the summary (posts index + important file previews + CI checks).")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_file = Path(args.out).resolve() if args.out else default_out_file(root)

    sections = gather_files(root)
    write_combined(root, out_file, sections, paths_only=args.paths_only, summary_only=args.summary_only)

if __name__ == "__main__":
    sys.exit(main())