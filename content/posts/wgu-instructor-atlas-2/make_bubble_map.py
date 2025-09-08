#!/usr/bin/env python3
# Requires: pandas>=2.0, folium>=0.16

import json, math
import pandas as pd
import folium

# Paths (adjust for your machine)
CSV_PATH = "path/to/2025_06_instructors.csv"
MAP_JSON = "path/to/uni_geo_mapping.json"
OUT_JOINED = "path/to/university_counts_with_geo.csv"
OUT_BUBBLE = "path/to/university_bubble_map.html"

# 1) counts per university
df = pd.read_csv(CSV_PATH)
counts = df.groupby("university", dropna=True).size().reset_index(name="count")

# 2) load geocode cache
with open(MAP_JSON, "r") as f:
    m = json.load(f)

geo = pd.DataFrame([
    {"university": k,
     "lat": v.get("lat"),
     "lng": v.get("lng"),
     # Keep place_id private in the published CSV
     "formatted_address": v.get("formatted_address")}
    for k, v in m.items()
])

# 3) join and write a public-safe CSV
joined = counts.merge(geo, on="university", how="left")
pub_cols = ["university", "count", "lat", "lng", "formatted_address"]
joined[pub_cols].to_csv(OUT_JOINED, index=False)

# 4) filter mapped rows
plot_df = joined.dropna(subset=["lat","lng"]).copy()

# 5) map center and options
center = [plot_df["lat"].mean(), plot_df["lng"].mean()]

def bubble_radius(c):  # size ~ sqrt(count)
    return 4 + 3 * math.sqrt(max(int(c), 1))

mapp = folium.Map(
    location=center, zoom_start=4, tiles="cartodbpositron",
    world_copy_jump=True  # nicer panning
)

# 6) markers
for _, r in plot_df.iterrows():
    folium.CircleMarker(
        location=[float(r["lat"]), float(r["lng"])],
        radius=bubble_radius(r["count"]),
        fill=True, fill_opacity=0.6, weight=1,
        popup=f'{r["university"]} — {int(r["count"])} instructors'
    ).add_to(mapp)

# Optional: constrain panning to plotted points
try:
    bounds = [[plot_df["lat"].min(), plot_df["lng"].min()],
              [plot_df["lat"].max(), plot_df["lng"].max()]]
    mapp.fit_bounds(bounds, padding=(20, 20))
except Exception:
    pass

mapp.save(OUT_BUBBLE)

print(f"Wrote: {OUT_BUBBLE}")
print(f"Joined table: {OUT_JOINED}")
missing = joined["lat"].isna().sum()
if missing:
    print(f"Warning: {missing} universities missing coordinates")