import csv
import requests
import time
import random
import json
import os

# Paths (relative)
DATA_DIR = "instructor_data"
CSV_INPUT = os.path.join(DATA_DIR, "instructor_research.csv")
JSON_OUTPUT = os.path.join(DATA_DIR, "instructor_papers.json")
SUMMARY_OUTPUT = os.path.join(DATA_DIR, "fetch_summary.txt")

BASE_URL = "https://api.semanticscholar.org/graph/v1"
HEADERS = {}

LIMIT = 300000  # Limit authors to fetch for testing

def fetch_papers(author_id):
    url = f"{BASE_URL}/author/{author_id}"
    params = {
        "fields": "name,papers.title,papers.year,papers.abstract,papers.url,papers.fieldsOfStudy"
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print("Rate limit hit. Sleeping 10 seconds.")
            time.sleep(10)
            return {}
        else:
            print(f"Request failed ({resp.status_code}) for author ID {author_id}")
            return {}
    except Exception as e:
        print(f"Exception fetching author ID {author_id}: {e}")
        return {}

# Load existing paper data
if os.path.exists(JSON_OUTPUT):
    with open(JSON_OUTPUT, 'r', encoding='utf-8') as f:
        author_data = json.load(f)
else:
    author_data = {}

# Stats tracking
stats = {
    "total_instructors": 0,
    "authors_with_profiles": 0,
    "authors_processed": 0,
    "authors_with_papers": 0,
    "total_papers": 0,
    "missing_title": 0,
    "missing_year": 0,
    "missing_abstract": 0,
    "missing_url": 0,
    "missing_fieldsOfStudy": 0
}

# First pass: count instructors and those with matched_url
with open(CSV_INPUT, newline='', encoding='utf-8') as infile:
    reader = list(csv.DictReader(infile))
    stats["total_instructors"] = len(reader)
    stats["authors_with_profiles"] = sum(1 for row in reader if row.get("matched_url", "").strip())

# Second pass: fetch data
count = 0
with open(CSV_INPUT, newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    for row in reader:
        name = f"{row['first_name']} {row['last_name']}"
        url = row.get("matched_url", "").strip()
        if not url or name in author_data:
            continue

        author_id = url.rstrip("/").split("/")[-1]
        print(f"[{count+1}] Fetching papers for: {name} (ID: {author_id})")

        data = fetch_papers(author_id)
        if data:
            papers = data.get("papers", [])
            if papers:
                stats["authors_with_papers"] += 1

            paper_entries = []
            for p in papers:
                if not p.get("title"):
                    stats["missing_title"] += 1
                if not p.get("year"):
                    stats["missing_year"] += 1
                if not p.get("abstract"):
                    stats["missing_abstract"] += 1
                if not p.get("url"):
                    stats["missing_url"] += 1
                if not p.get("fieldsOfStudy"):
                    stats["missing_fieldsOfStudy"] += 1

                paper_entries.append({
                    "title": p.get("title", ""),
                    "year": p.get("year", ""),
                    "abstract": p.get("abstract", ""),
                    "url": p.get("url", ""),
                    "fieldsOfStudy": p.get("fieldsOfStudy", [])
                })

            author_data[name] = {"papers": paper_entries}
            stats["total_papers"] += len(paper_entries)

            print(f"  → {len(paper_entries)} papers found")
            stats["authors_processed"] += 1
            count += 1

        time.sleep(random.uniform(1.0, 2.0))
        if count >= LIMIT:
            break

# Save updated JSON
with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(author_data, f, indent=2)

# Save summary
summary_lines = [
    "FETCH SUMMARY",
    "=============",
    f"\nInput file: {CSV_INPUT}",
    f"Output file: {JSON_OUTPUT}",
    f"\nTotal instructors in CSV:        {stats['total_instructors']}",
    f"Instructors with profile URLs:   {stats['authors_with_profiles']}",
    f"Instructors processed:           {stats['authors_processed']}",
    f"Instructors with papers:         {stats['authors_with_papers']}",
    f"\nTotal papers fetched:            {stats['total_papers']}",
    f"Papers missing titles:           {stats['missing_title']}",
    f"Papers missing years:            {stats['missing_year']}",
    f"Papers missing abstracts:        {stats['missing_abstract']}",
    f"Papers missing URLs:             {stats['missing_url']}",
    f"Papers missing fieldsOfStudy:    {stats['missing_fieldsOfStudy']}"
]

with open(SUMMARY_OUTPUT, 'w', encoding='utf-8') as f:
    f.write("\n".join(summary_lines))

print("\n".join(summary_lines))