#!/usr/bin/env python3
# base_parser.py — minimal parser assuming well-formed structure

import re
from collections import Counter, defaultdict
from pathlib import Path

# inputs / constants
infile = Path("instructor_data_raw.txt")
EXPECTED_TOTAL = 1159  # total input lines for June 2025

catalog_headers = (
    "Instructor Directory", "General Education", "School of Business",
    "Leavitt School of Health", "School of Technology",
    "School of Education", "WGU Academy"
)
footer_re = re.compile(r"^©\s*Western Governors University\b.*\d{1,4}$")

# tallies
counts = Counter(
    total_lines=0,
    title_lines=0,
    college_header_lines=0,
    footer_lines=0,
    instructor_lines=0,
    blank_lines=0,
    other_lines=0,
)

sections = []                    # ordered list of detected colleges
samples = defaultdict(list)      # college -> a few example rows
records = []                     # full parsed rows (name, degree, university, college)

current_college = None

with infile.open("r", encoding="utf-8") as f:
    for lineno, raw in enumerate(f, start=1):
        counts["total_lines"] += 1
        s = raw.strip()
        if not s:
            counts["blank_lines"] += 1
            continue

        # skip page footer lines
        if footer_re.match(s):
            counts["footer_lines"] += 1
            continue

        # catalog headers
        if s in catalog_headers:
            if s == "Instructor Directory":
                counts["title_lines"] += 1
            else:
                counts["college_header_lines"] += 1
                current_college = s
                sections.append(s)
            continue

        # instructor rows are "Last, First; Degree, University"
        if ";" in s:
            name_part, right = s.split(";", 1)
            last, first = [x.strip() for x in name_part.split(",", 1)]
            degree, university = [x.strip() for x in right.split(",", 1)]

            rec = {
                "college": current_college,
                "last_name": last,
                "first_names": first,
                "degree": degree,
                "university": university,
                "lineno": lineno,
            }
            records.append(rec)
            counts["instructor_lines"] += 1

            if len(samples[current_college]) < 3:
                samples[current_college].append({
                    "name": f"{last}, {first}",
                    "degree": degree,
                    "university": university,
                })
            continue

        # any other content is counted but ignored
        counts["other_lines"] += 1

# ---------- output (terminal) ----------

print("Instructor Directory\n")
for sec in sections:
    print(sec)
    print("name | degree | university")
    for r in samples[sec]:
        print(f"{r['name']} | {r['degree']} | {r['university']}")
    print()

# simple validation: reconstructed total equals expected
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
print(f"status: {'OK' if (counts['total_lines'] == EXPECTED_TOTAL == recon) else 'MISMATCH'}")