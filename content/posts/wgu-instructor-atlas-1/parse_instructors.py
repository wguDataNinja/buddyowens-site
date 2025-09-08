#!/usr/bin/env python3
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


infile = Path("instructor_data_raw.txt")

# config
DEBUG = True
EXPECTED_TOTAL = 1159
SAMPLES_PER_SECTION = 3

# anchors / headers
copyright_anchor = "©"
catalog_headers = {
    "Instructor Directory",
    "General Education",
    "School of Business",
    "Leavitt School of Health",
    "School of Technology",
    "School of Education",
    "WGU Academy",
}

# degree hints (prefixes we’ll recognize even if comma is missing)
DEGREE_PREFIXES = [
    "PhD", "EdD", "DBA", "MBA", "MA", "MS", "M.S.", "MEd", "M.Ed.", "MLIS", "MPA",
    "BS", "B.S.", "BA", "B.A.", "Doctorate Degree", "Master's Degree", "Bachelor's Degree",
    "EdS", "MSEd", "MSCS", "MSIT", "MSN", "DNP", "JD", "MD"
]
deg_prefix_rx = re.compile(r"^(" + "|".join(map(re.escape, DEGREE_PREFIXES)) + r")\b")

name_comma_rx = re.compile(r'^\s*([^,]+),\s*(.+?)\s*$')

def parse_name(name_part, lineno):
    # tolerate "Clark. Traci" -> "Clark, Traci"
    if ". " in name_part and "," not in name_part:
        fixed = name_part.replace(". ", ", ", 1)
        if DEBUG:
            print(f"[FIX] L{lineno}: replaced '. ' with ', ' in name -> {fixed}")
        name_part = fixed
    m = name_comma_rx.match(name_part.strip())
    if m:
        last, firsts = m.groups()
        return last.strip(), firsts.strip(), None
    if DEBUG:
        print(f"[WARN] L{lineno}: name not in 'Last, First' -> {name_part.strip()}")
    parts = name_part.strip().split()
    if len(parts) == 1:
        return parts[0], None, "single_token"
    return parts[0], " ".join(parts[1:]), "no_comma"

def split_right(right, lineno):
    """
    Return (degree, university, flag) handling:
      'Degree, University'
      'Degree University'  [missing comma]
      'University'         [no degree]
    """
    right = right.strip()

    if "," in right:
        degree, university = right.split(",", 1)
        return degree.strip(), university.strip(), None

    m = deg_prefix_rx.match(right)
    if m:
        deg = m.group(1)
        rest = right[m.end():].strip()
        if not rest:
            if DEBUG:
                print(f"[WARN] L{lineno}: degree found but university missing -> {right}")
        else:
            if DEBUG:
                print(f"[FIX] L{lineno}: parsed degree without comma -> {deg} | {rest}")
        return deg, (rest or None), "missing_comma"

    if DEBUG:
        print(f"[FIX] L{lineno}: no degree present, using university only -> {right}")
    return None, right, "no_degree"

# counters
counts = Counter(
    total_lines=0,
    title_lines=0,
    college_header_lines=0,
    footer_lines=0,
    instructor_lines=0,
    blank_lines=0,
    other_lines=0,
)

by_college = Counter()
sections = []                   # ordered list of detected colleges
samples = defaultdict(list)     # college -> sample rows
records = []                    # full parsed rows for downstream use

current_college = None
saw_title = False

with infile.open("r", encoding="utf-8") as f:
    for lineno, raw in enumerate(f, start=1):
        line = raw.rstrip("\n")
        counts["total_lines"] += 1
        s = line.strip()

        if not s:
            counts["blank_lines"] += 1
            continue

        # robust footer skip: any line that starts with © and mentions WGU
        if s.startswith(copyright_anchor) and "Western Governors University" in s:
            counts["footer_lines"] += 1
            continue

        # headers
        if s in catalog_headers:
            if s == "Instructor Directory":
                counts["title_lines"] += 1
                saw_title = True
            else:
                counts["college_header_lines"] += 1
                current_college = s
                sections.append(s)
            continue

        # ignore filler like "...."
        if set(s) == {"."}:
            counts["other_lines"] += 1
            continue

        # instructor row must have a ';'
        if ";" not in s:
            counts["other_lines"] += 1
            if DEBUG:
                print(f"[INFO] L{lineno}: non-instructor line kept in totals -> {s}")
            continue

        # parse
        name_part, right = s.split(";", 1)
        last, firsts, name_flag = parse_name(name_part, lineno)
        degree, university, right_flag = split_right(right, lineno)

        if not current_college:
            # tolerate out-of-section instructor (shouldn't happen in this doc)
            current_college = "Unknown"

        # store for downstream use
        rec = {
            "college": current_college,
            "last_name": last,
            "first_names": firsts,
            "degree": degree,
            "university": university,
            "lineno": lineno,
        }
        records.append(rec)

        counts["instructor_lines"] += 1
        by_college[current_college] += 1

        # keep a few samples per section
        if len(samples[current_college]) < SAMPLES_PER_SECTION:
            samples[current_college].append({
                "name": f"{last}" + (f", {firsts}" if firsts else ""),
                "degree": degree or "(none)",
                "university": university or "(none)",
            })

        # granular debug notes
        if DEBUG and (name_flag or right_flag):
            nf = f"name={name_flag}" if name_flag else ""
            rf = f"right={right_flag}" if right_flag else ""
            tag = ", ".join(x for x in (nf, rf) if x)
            print(f"[NOTE] L{lineno}: tolerant parse -> {tag}")

# ---------- OUTPUT (terminal) ----------

# top: show title then each college with a few rows
print("Instructor Directory\n")

for sec in sections:
    print(sec)
    print("name | degree | university")
    for r in samples[sec]:
        print(f"{r['name']} | {r['degree']} | {r['university']}")
    print()  # blank line between sections

# summary and validation
recon = (
    counts["instructor_lines"]
    + counts["title_lines"]
    + counts["college_header_lines"]
    + counts["footer_lines"]
    + counts["blank_lines"]
    + counts["other_lines"]
)

print("== Parse Summary ==")
print(f"Total input lines: {counts['total_lines']}")
print(f"Title lines: {counts['title_lines']}")
print(f"College header lines: {counts['college_header_lines']}")
print(f"Footer lines (skipped): {counts['footer_lines']}")
print(f"Instructor rows parsed: {counts['instructor_lines']}")
print(f"Blank lines: {counts['blank_lines']}")
print(f"Other lines: {counts['other_lines']}")

print("\nParse validation:")
print(f"expected total: {EXPECTED_TOTAL}")
print(f"reconstructed sum: {recon}")
status = "OK" if (counts["total_lines"] == EXPECTED_TOTAL == recon) else "MISMATCH"
print(f"status: {status}")

# additional tight check: sum of section counts equals parsed rows
by_college_sum = sum(by_college.values())
rows_ok = "OK" if by_college_sum == counts["instructor_lines"] else "MISMATCH"
print(f"by_college sum: {by_college_sum}  vs parsed rows: {counts['instructor_lines']}  check: {rows_ok}")

# exit non-zero if mismatched (useful in CI)
if not (status == "OK" and rows_ok == "OK"):
    sys.exit(1)