+++
title = "WGU Instructor Atlas Part 2 - Geocoding"
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
Scraping the WGU Catalog Part 2 of 3: Geocode alma mater university locations using the Google Maps API


## Interactive Map
{{< iframe_res src="maps/university_bubble_map.html" title="WGU Instructor Alma Maters — Bubble Map" >}}

---

## From Part 1: Scraping the Catalog  
In [Part 1](../wgu-instructor-atlas-1/), we parsed the June 2025 catalog into a clean dataset of WGU instructors and their alma maters:  
[2025_06_instructors.csv](../wgu-instructor-atlas-1/2025_06_instructors.csv).  

That CSV serves as the input here. Each university name is geocoded to latitude/longitude coordinates, producing an interactive map of instructor origins.  

---

## Geocoding the Universities  

Each unique university name (~350 total) was passed through the **Google Maps Geocoding API**.  
Key features of the pipeline:  

- **API key management** — kept in `config.yaml`, never hard-coded.  
- **Caching** — results saved to [uni_geo_mapping.json](uni_geo_mapping.json) so each university is only geocoded once.  
- **Overrides** — `uni_overrides.csv` provides corrected queries (e.g. “UCLA” → “University of California, Los Angeles”).  
- **Manual fixes** — a handful of unmatched names (typos, obscure schools) were cleaned by hand.  

Example geocoding output (as stored in JSON):  
```json
{
  "Stanford University": {
    "query": "Stanford University",
    "formatted_address": "450 Serra Mall, Stanford, CA 94305, USA",
    "lat": 37.4274745,
    "lng": -122.169719,
    "place_id": "ChIJ9T_5iuTKj4AR1p1nTSaRtuQ",
    "source": "geocoding"
  }
}
```
---

## Building the Bubble Map  

Once universities were geocoded, we joined counts to coordinates:  

```python
counts = df.groupby("university").size().reset_index(name="count")
geo = pd.DataFrame.from_dict(mapping, orient="index")
joined = counts.merge(geo, on="university")
```
From there, we built an interactive map with **Folium**:  

- Circle markers at each lat/lng  
- Bubble radius proportional to sqrt(count)  
- Popup with university name + instructor count  
- Carto Positron tiles for clean basemap  
- Auto-fit bounds so all points are visible  
```python
folium.CircleMarker(
    location=[r["lat"], r["lng"]],
    radius=4 + 3*math.sqrt(r["count"]),
    fill=True, fill_opacity=0.6,
    popup=f'{r["university"]} — {r["count"]} instructors'
).add_to(mapp)
```

Outputs:
- `university_counts_with_geo.csv` — counts + coordinates
- `university_bubble_map.html` — interactive bubble map
- `make_bubble_map.py` — rendering script


## Outputs  

- [university_counts_with_geo.csv](university_counts_with_geo.csv) — counts with coordinates  
- [university_bubble_map.html](/maps/university_bubble_map.html) — interactive bubble map  
- [make_bubble_map.py](../wgu-instructor-atlas-2/make_bubble_map.py) — pipeline script  

---

## Notes 

- ~350 universities successfully mapped  
- Total cost: **$0** (fully within free tier)  
- Map shows instructor clusters across the U.S. with a handful abroad  

## Next in the Series

In **Part 3**, we’ll look to the **research output of WGU faculty**.  
Using the [Semantic Scholar API](https://api.semanticscholar.org/), we:  
- Query by instructor name and institution to identify published works  
- Build a reproducible archive of journal articles, conference papers, and books  
- Link each publication back to the normalized instructor dataset  
- Export both a CSV and a searchable interface for browsing WGU faculty research  

Read here: [WGU Instructor Atlas 3 — Research Archive](../wgu-instructor-atlas-3/)