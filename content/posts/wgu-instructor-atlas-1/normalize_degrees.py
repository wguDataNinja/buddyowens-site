#!/usr/bin/env python3
"""
Standalone script to build cleaned and aggregated datasets for instructor visuals.
"""

import json
import os
from pathlib import Path
import numpy as np
import pandas as pd

# === Paths ===
BASE_DIR = Path("/Users/buddy/Desktop/WGU-Reddit/WGU_catalog/instructor_directory")
INPUT_FILE = BASE_DIR / "2025_06_instructors.csv"
OUTPUT_DIR = BASE_DIR / "viz_data"

# Degree mapping dictionary
DEGREE_MAP = {
    "Doctorate Degree": "PhD", "PhD": "PhD", "EdD": "EdD", "DBA": "DBA",
    "DNP": "DNP", "JD": "JD", "MD": "MD", "EdS": "EdS",
    "Master's Degree": "Master", "MA": "MA", "MS": "MS", "MBA": "MBA",
    "MEd": "MEd", "MSEd": "MEd", "MPA": "MPA", "MPH": "MPH", "MSN": "MSN",
    "MLIS": "MLIS", "MSIT": "MSIT", "MSCS": "MSCS",
    "Bachelor's Degree": "Bachelor", "BA": "BA", "BS": "BS", "BSN": "BSN",
    "Associate's Degree": "Associate", "AA": "AA", "AS": "AS"
}

DOCTORATE_TITLES = {"PHD", "EDD", "DBA", "DNP", "JD", "MD"}
MASTER_TITLES = {"MASTER", "MA", "MS", "MBA", "MED", "MPA", "MPH", "MSN", "MLIS", "MSIT", "MSCS"}
BACHELOR_TITLES = {"BACHELOR", "BA", "BS", "BSN"}
ASSOCIATE_TITLES = {"ASSOCIATE", "AA", "AS"}


def normalize_str(x):
    if pd.isna(x):
        return None
    return " ".join(str(x).strip().split())


def infer_degree_level(standard):
    if not standard:
        return "unknown"
    u = standard.upper()
    if u in DOCTORATE_TITLES:
        return "doctorate"
    if u in MASTER_TITLES:
        return "master"
    if u in BACHELOR_TITLES:
        return "bachelor"
    if u in ASSOCIATE_TITLES:
        return "associate"
    return "unknown"


def shannon_entropy(proportions):
    p = proportions[proportions > 0]
    return float(-(p * np.log(p)).sum()) if p.size else 0.0


def clean_inputs(df):
    for col in ["first_name", "last_name", "college", "degree", "degree_level", "university"]:
        df[col] = df[col].apply(normalize_str)

    df["degree_standard"] = df["degree"].apply(
        lambda s: DEGREE_MAP.get((s or "").strip(), normalize_str(s))
    )

    df["degree_level"] = df["degree_level"].str.lower()
    df["degree_level"] = df.apply(
        lambda r: r["degree_level"] if r["degree_level"] in {"doctorate", "master", "bachelor", "associate"}
        else infer_degree_level(r["degree_standard"]),
        axis=1
    )

    df["faculty_id"] = pd.util.hash_pandas_object(
        df[["first_name", "last_name", "college", "degree", "university"]].astype(str),
        index=False
    ).astype("int64").astype("string")

    return df[["faculty_id", "first_name", "last_name", "college",
               "degree", "degree_standard", "degree_level", "university"]]


def degree_level_by_college(df):
    return df.groupby(["college", "degree_level"], as_index=False)["faculty_id"].nunique() \
             .rename(columns={"faculty_id": "count"})


def college_profile(df):
    lvl = degree_level_by_college(df)
    fac = df.groupby("college", as_index=False)["faculty_id"].nunique() \
            .rename(columns={"faculty_id": "faculty_count"})
    idx = lvl.groupby("college")["count"].idxmax()
    dom = lvl.loc[idx, ["college", "degree_level", "count"]] \
             .rename(columns={"degree_level": "dominant_level", "count": "dominant_count"})
    prof = fac.merge(dom, on="college", how="left")
    prof["dominant_share"] = (prof["dominant_count"] / prof["faculty_count"]).round(3)
    return prof.drop(columns=["dominant_count"])


def top_feeders(df):
    return df.groupby("university", as_index=False)["faculty_id"].nunique() \
             .rename(columns={"faculty_id": "count"}) \
             .sort_values("count", ascending=False)


def degree_titles_by_college_top(df, top_n=30):
    t = df.groupby("degree_standard", as_index=False)["faculty_id"].nunique() \
          .rename(columns={"faculty_id": "count"})
    top_titles = set(t.sort_values("count", ascending=False).head(top_n)["degree_standard"])
    return df[df["degree_standard"].isin(top_titles)] \
        .groupby(["college", "degree_standard"], as_index=False)["faculty_id"].nunique() \
        .rename(columns={"faculty_id": "count"})


def college_diversity(df):
    records = []
    for college, sub in df.groupby("college"):
        fac_count = sub["faculty_id"].nunique()
        counts = sub.groupby("degree_standard")["faculty_id"].nunique().values.astype(float)
        proportions = counts / counts.sum() if counts.sum() else np.array([])
        entropy = shannon_entropy(proportions)
        doc_count = sub[sub["degree_level"] == "doctorate"]["faculty_id"].nunique()
        pct_doc = (doc_count / fac_count) if fac_count else 0.0
        records.append({
            "college": college,
            "diversity_index": round(entropy, 4),
            "faculty_count": fac_count,
            "pct_doctorate": round(pct_doc, 4)
        })
    return pd.DataFrame.from_records(records)


def rare_degrees(df):
    c = df.groupby("degree_standard", as_index=False)["faculty_id"].nunique() \
          .rename(columns={"faculty_id": "count"})
    rare = c[c["count"] <= 3].copy()
    rare["rarity_bucket"] = np.where(rare["count"] == 1, "singleton", "low")
    return rare.sort_values(["rarity_bucket", "count", "degree_standard"])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_FILE)
    df_clean = clean_inputs(df)
    df_clean.to_csv(OUTPUT_DIR / "cleaned_instructors.csv", index=False)

    degree_level_by_college(df_clean).to_csv(OUTPUT_DIR / "degree_level_by_college.csv", index=False)
    college_profile(df_clean).to_csv(OUTPUT_DIR / "college_profile.csv", index=False)
    top_feeders(df_clean).to_csv(OUTPUT_DIR / "top_feeders.csv", index=False)
    degree_titles_by_college_top(df_clean).to_csv(OUTPUT_DIR / "degree_titles_by_college_top30.csv", index=False)
    college_diversity(df_clean).to_csv(OUTPUT_DIR / "college_diversity.csv", index=False)
    rare_degrees(df_clean).to_csv(OUTPUT_DIR / "rare_degrees.csv", index=False)

    print(f"Data processing complete. Outputs saved to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()