+++
title = "WGU Instructor Atlas 2 — Geocoding and Maps"
date = 2025-08-22T14:42:00-04:00
draft = false
tags = ['geocoding', 'WGU-catalog']
series = ["WGU Instructor Atlas"]
[cover]
relative = true
hidden = false
hiddenInList = false
hiddenInSingle = false
+++

# Geocoding and Maps

In Part 2, I map WGU instructor alma maters by geocoding each university from the cleaned CSV.  
The output is a reproducible pipeline that generates an **interactive bubble map** showing where instructors earned their degrees.

<!--more-->


## Interactive Map
{{< iframe_res src="maps/university_bubble_map.html" title="WGU Instructor Alma Maters — Bubble Map" >}}

---
## Geocoding the Universities

To locate each institution, I used the **Google Maps Geocoding API**.  
- Created a Google Cloud project and enabled the Geocoding service.  
- Generated an API key and stored it in `apikey.yaml` (kept private).  
- Google provides $200 of free credit per month; all ~350 unique lookups for this dataset stayed well within the free tier.  
- Results were cached in `uni_geo_mapping.json` to avoid duplicate requests.  
- A few ambiguous names were corrected with manual overrides.  

---

## Data Flow

- Output CSV: [university_counts_with_geo.csv](university_counts_with_geo.csv)  
- Interactive map: [/maps/university_bubble_map.html](/maps/university_bubble_map.html)  

---

## Script

- [`make_bubble_map.py`](make_bubble_map.py) — reads the instructor CSV, joins counts with cached coordinates, writes the joined dataset, and produces the interactive bubble map.

---

## Notes and Next

- ~350 unique universities successfully mapped after a few manual fixes  
- Total cost: **$0** (entirely within Google’s free tier)  
- The bubble map highlights instructor clusters across the U.S. with a handful abroad  

## Next in the Series

In **Part 3**, we’ll move beyond alma maters to the **research output of WGU faculty**.  
Using the [Semantic Scholar API](https://api.semanticscholar.org/), I’ll:  
- Query by instructor name and institution to identify published works  
- Build a reproducible archive of journal articles, conference papers, and books  
- Link each publication back to the normalized instructor dataset  
- Export both a CSV and a searchable interface for browsing WGU faculty research  

Read here: [WGU Instructor Atlas 3 — Research Archive](../wgu-instructor-atlas-3/)