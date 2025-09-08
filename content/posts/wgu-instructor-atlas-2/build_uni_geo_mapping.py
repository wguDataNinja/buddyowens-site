#!/usr/bin/env python3
import json, time, pathlib, sys
import pandas as pd
import requests
import yaml

CSV_PATH = "/WGU_catalog/instructor_directory/instructor_data/2025_06_instructors.csv"
KEY_YAML = "/Users/buddy/Desktop/WGU-Reddit/WGU_catalog/geomapping/config.yaml"
OUT_JSON = "/Users/buddy/Desktop/WGU-Reddit/WGU_catalog/geomapping/uni_geo_mapping.json"
UNMATCHED_TXT = "/Users/buddy/Desktop/WGU-Reddit/WGU_catalog/geomapping/unmatched_universities.txt"
OVERRIDES_CSV = "/Users/buddy/Desktop/WGU-Reddit/WGU_catalog/geomapping/uni_overrides.csv"

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

def load_key(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)["google_api_key"]

def load_existing(path):
    p = pathlib.Path(path)
    if p.exists():
        with open(p, "r") as f:
            return json.load(f)
    return {}

def load_overrides(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return dict(zip(
        df["original"].astype(str).str.strip(),
        df["geocode_query"].astype(str).str.strip()
    ))

def geocode_via_geocoding(name, api_key):
    params = {
        "address": name,
        "key": api_key,
        "region": "us",
        "components": "country:US"
    }
    r = requests.get(GEOCODE_URL, params=params, timeout=20)
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    res = data["results"][0]
    loc = res["geometry"]["location"]
    return {
        "query": name,
        "formatted_address": res.get("formatted_address"),
        "place_id": res.get("place_id"),
        "lat": loc["lat"],
        "lng": loc["lng"],
        "types": res.get("types", []),
        "source": "geocoding"
    }

def geocode_via_places(name, api_key):
    fp = requests.get(FIND_PLACE_URL, params={
        "input": name,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address,types",
        "key": api_key
    }, timeout=20).json()
    cand = (fp.get("candidates") or [])
    if not cand:
        return None
    pid = cand[0]["place_id"]
    det = requests.get(DETAILS_URL, params={
        "place_id": pid,
        "fields": "name,formatted_address,geometry/location,types",
        "key": api_key
    }, timeout=20).json()
    if det.get("status") != "OK" or "result" not in det:
        return None
    r = det["result"]
    loc = r["geometry"]["location"]
    return {
        "query": name,
        "formatted_address": r.get("formatted_address"),
        "place_id": pid,
        "lat": loc["lat"],
        "lng": loc["lng"],
        "types": r.get("types", []),
        "source": "places"
    }

def geocode(name, api_key, retries=3, sleep_sec=0.25):
    # try Geocoding first
    for attempt in range(retries):
        x = geocode_via_geocoding(name, api_key)
        if x: return x
        time.sleep(sleep_sec * (attempt + 1))
    # fallback to Places
    for attempt in range(retries):
        x = geocode_via_places(name, api_key)
        if x: return x
        time.sleep(sleep_sec * (attempt + 1))
    return None

def main():
    api_key = load_key(KEY_YAML)
    overrides = load_overrides(OVERRIDES_CSV)

    df = pd.read_csv(CSV_PATH)
    df["university"] = df["university"].astype(str).str.strip()

    # known typo guard (seen earlier)
    df.loc[df["university"].eq("versity of California, Santa Barbara"),
           "university"] = "University of California, Santa Barbara"

    universities = (
        df["university"]
        .dropna()
        .loc[lambda s: s != ""]
        .unique()
        .tolist()
    )

    mapping = load_existing(OUT_JSON)
    unmatched = []

    # decide query string (override if present)
    query_for = {u: overrides.get(u, u) for u in universities}

    to_do = [u for u in universities if u not in mapping]
    print(f"Unique universities: {len(universities)} | remaining to geocode: {len(to_do)}")

    for i, uni in enumerate(to_do, 1):
        info = geocode(query_for[uni], api_key)
        if info:
            mapping[uni] = info
        else:
            unmatched.append(uni)

        if i % 25 == 0:
            with open(OUT_JSON, "w") as f:
                json.dump(mapping, f, indent=2)
            print(f"Checkpoint saved at {i} lookups")
        time.sleep(0.25)  # gentle pacing

    with open(OUT_JSON, "w") as f:
        json.dump(mapping, f, indent=2)

    with open(UNMATCHED_TXT, "w") as f:
        f.write("\n".join(unmatched))

    print(f"Done. Saved {len(mapping)} entries to {OUT_JSON}")
    print(f"{len(unmatched)} unmatched saved to {UNMATCHED_TXT}")

if __name__ == "__main__":
    sys.exit(main())