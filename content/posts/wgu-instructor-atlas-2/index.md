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

## Geocoding and Maps  
Part 2 of 3: Geocode alma mater university locations using the Google Maps API to produce an interactive bubble map of WGU instructors’ degrees.  
<!--more-->


## Interactive Map
{{< iframe_res src="maps/university_bubble_map.html" title="WGU Instructor Alma Maters — Bubble Map" >}}

---## From Part 1: Scraping the Catalog  
In [Part 1](../wgu-instructor-atlas-1/), we parsed the June 2025 catalog into a clean dataset of WGU instructors and their alma maters:  
[2025_06_instructors.csv](../wgu-instructor-atlas-1/2025_06_instructors.csv).  

That CSV serves as the input here. Each university name is geocoded to latitude/longitude coordinates, producing an interactive map of instructor origins.  

---

## Geocoding the Universities  

Using the **Google Maps Geocoding API**:  
- Enabled the service in a Google Cloud project  
- Stored the API key privately in `apikey.yaml`  
- ~350 unique lookups, all within the free $200/month credit  
- Cached results in `uni_geo_mapping.json`  
- Corrected a handful of ambiguous names manually  

---

## Outputs  

- [university_counts_with_geo.csv](university_counts_with_geo.csv) — counts with coordinates  
- [university_bubble_map.html](/maps/university_bubble_map.html) — interactive bubble map  
- [make_bubble_map.py](../wgu-instructor-atlas-2/make_bubble_map.py) — pipeline script  

---

## Notes and Next  

- ~350 universities successfully mapped  
- Total cost: **$0** (fully within free tier)  
- Map shows instructor clusters across the U.S. with a handful abroad  

## Next in the Series

In **Part 3**, we’ll move beyond alma maters to the **research output of WGU faculty**.  
Using the [Semantic Scholar API](https://api.semanticscholar.org/), we:  
- Query by instructor name and institution to identify published works  
- Build a reproducible archive of journal articles, conference papers, and books  
- Link each publication back to the normalized instructor dataset  
- Export both a CSV and a searchable interface for browsing WGU faculty research  

Read here: [WGU Instructor Atlas 3 — Research Archive](../wgu-instructor-atlas-3/)