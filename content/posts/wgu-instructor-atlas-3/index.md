+++
title = "WGU Instructor Atlas Part 3 — Research Archive"
date = 2025-09-01T01:13:26-04:00
draft = false
tags = ['semantic-scholar','WGU-research']
series = ["WGU Instructor Atlas"]
[cover]
relative = true
hidden = false
hiddenInList = false
hiddenInSingle = false
+++

## Fetching Publications  
Scraping the WGU Catalog Part 3 of 3: match instructors to Semantic Scholar and fetch publication metadata for a searchable archive.

---

## Outputs  
- `instructor_papers.json` — instructor → papers mapping  
- `fetch_publications.py` — publication fetcher

---

## Quick Example (archive structure)  
```json
{
  "Brent Albrecht": {
    "papers": [
      {
        "title": "Dependence of UO2 surface morphology on processing history within a single synthetic route",
        "year": 2019,
        "abstract": "Abstract This study aims to determine forensic signatures ...",
        "url": "https://www.semanticscholar.org/paper/f7a6e71e16a167aab30b9b68023679dbda18accf",
        "fieldsOfStudy": ["Chemistry"]
      }
    ]
  }
}
```

## From Part 2: Geocoding Alma Maters  
In [Part 2](../wgu-instructor-atlas-2/), we geocoded ~350 alma mater universities and built an interactive map of instructor origins.  

Now we take the same instructor dataset and enrich it with **research output**. Each instructor is matched to a Semantic Scholar profile, and their publications are fetched into a structured archive.  

---

## Semantic Scholar API  

We use the [Semantic Scholar Graph API](https://www.semanticscholar.org/product/api%2Ftutorial) to link instructors with research output:  

- **Author Search**: `GET /author/search` by name + university  
- **Author Details**: `GET /author/{id}` with fields like `papers.title`, `papers.year`, `papers.abstract`, `papers.url`, and `papers.fieldsOfStudy`  

Key features of the pipeline:  
- Match instructors to author profiles via fuzzy name search  
- Resolve Semantic Scholar `authorId` and profile URL  
- Fetch all available papers with metadata  
- Save as structured JSON with QA summary  

---

## Author Matching  

Each instructor from the catalog CSV is queried against the API with both name and institution:  

```python
# Simplified excerpt (see fetch_profile.py)
candidates = search_author("Jane Smith Western Governors University")
match = best_match("Jane Smith", candidates)
```


Results are written to:
- `instructor_research.csv` - original instructor row plus matched_name and matched_url

Example row:

```text
first_name,last_name,university,matched_name,matched_url
Brent,Albrecht,Brigham Young University,Brent Albrecht,https://www.semanticscholar.org/author/2281351310

```


## Fetching Publications  

Matched authors are then resolved to their publications using the Semantic Scholar API.  

```python
# Simplified excerpt (see fetch_publications.py)
url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}"
params = {"fields": "name,papers.title,papers.year,papers.url,papers.fieldsOfStudy"}
resp = requests.get(url, params=params)
papers = resp.json().get("papers", [])
```

Each instructor’s works are saved in instructor_papers.json.

Example JSON entry:
```json
{
  "Brent Albrecht": {
    "papers": [
      {
        "title": "Dependence of UO2 surface morphology on processing history within a single synthetic route",
        "year": 2019,
        "abstract": "Abstract This study aims to determine forensic signatures ...",
        "url": "https://www.semanticscholar.org/paper/f7a6e71e16a167aab30b9b68023679dbda18accf",
        "fieldsOfStudy": ["Chemistry"]
      }
    ]
  }
}

```

## Next Steps: Toward a Searchable Research Archive  

The current archive links WGU instructors to thousands of papers, but it is not yet **easily searchable by topic**. The `fieldsOfStudy` values returned by Semantic Scholar are often too generic or inconsistent to drive meaningful exploration.  

### To-Do  
- Develop a consistent academic taxonomy and map papers into it  
- Re-classify papers when `fieldsOfStudy` is missing or vague  
- Enable filtering and search by discipline, subfield, or theme  

### Possible Approaches  
- **Use a pre-made taxonomy of academia**: examples include the **OECD Fields of Science and Technology (FOS)**, **UNESCO ISCED classifications**, or **Microsoft Academic Graph (MAG) fields**. These offer hierarchical categories (e.g. `Natural Sciences → Chemistry → Materials Science`).  
- **Leverage LLMs for classification**: prompt an LLM with paper title + abstract and map outputs into the chosen taxonomy.  
- **Hybrid strategy**: keep the existing `fieldsOfStudy` values when useful, but override or augment with LLM-based classification for precision.  

This will transform the publication archive from a static JSON dump into a structured, queryable index of WGU faculty research.  