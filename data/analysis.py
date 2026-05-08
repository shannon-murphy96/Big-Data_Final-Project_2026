#!/usr/bin/env python3

# analysis.py 
# Analyzes shellfish hatchery larval bioassay results to identify causative agents of crashes and where they're being introduced
# and determine the likely causative agent based on filtration size
# Research Question: Where do water quality issues arise in shellfish hatcheries
# (incoming water or tank water), and what is the likely causative
# agent based on which filter size still allows larval mortality to occur?
# Usage: python analysis.py [data file]
# Example: python analysis.py data/BHHC_data.csv
# Output: figures/ (heatmaps and bar chart) and tables/ (summary CSVs)

"""
Filter interpretation key:
    Unfiltered       -> parasite, bacteria, virus, toxin, or pollutant
    10um filter      -> bacteria, virus, toxin, or pollutant  (parasites removed)
    0.22um filter    -> virus, toxin, or pollutant            (bacteria removed)
    100 kDa filter   -> toxin or pollutant only               (viruses removed)

A treatment is flagged if average % mortality across the 3 replicates exceeds
10%. Comparing acute and chronic assay results distinguishes acute water quality
issues from chronic/husbandry/genetic problems.

Usage:
    python analysis.py <path_to_data_file>   # pass file path directly
    python analysis.py                        # will prompt you to enter the path

Example:
    python analysis.py data/BHHC_data.csv
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# ── Get the data file path ─────────────────────────────────────────────────────
# Accepts the file path two ways:
#   1. As a command-line argument: python analysis.py data/myfile.csv
#   2. Interactively: just run python analysis.py and it will ask you
if len(sys.argv) == 2:
    DATA_FILE = sys.argv[1]  # path provided on the command line
else:
    # No argument given — prompt the user to type the path
    DATA_FILE = input("Enter path to data file (e.g. data/BHHC_data.csv): ").strip()

# Check that the file actually exists before trying to load it
if not os.path.exists(DATA_FILE):
    print(f"Error: file not found: {DATA_FILE}")
    print("Please check the path and try again.")
    sys.exit(1)


# ── Output directories (relative to wherever the script is run from) ──────────
FIGURES_DIR = "figures"
TABLES_DIR = "tables"

# Create output folders if they don't already exist
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(TABLES_DIR, exist_ok=True)


# ── Constants ──────────────────────────────────────────────────────────────────
MORTALITY_THRESHOLD = 10  # avg % mortality above this is flagged as an issue

# Filter sizes listed from largest pore (most permissive) to smallest (most
# restrictive). Each filter removes progressively smaller agents.
FILTER_ORDER = ["Unfiltered", "10um filter", "0.22um filter", "100 kDa filter"]

# The likely causative agent for each filter level — based on what is still
# small enough to pass through that filter and potentially harm the larvae
CAUSATIVE_AGENT = {
    "Unfiltered":     "Parasite, bacteria, virus, toxin, or pollutant",
    "10um filter":    "Bacteria, virus, toxin, or pollutant",
    "0.22um filter":  "Virus, toxin, or pollutant",
    "100 kDa filter": "Toxin or pollutant",
}


# ── Load data ──────────────────────────────────────────────────────────────────
# The CSV has an embedded summary table to the right of the main data.
# Reading only the first 18 columns avoids loading that extra content.
df = pd.read_csv(DATA_FILE, usecols=range(18))

print(f"Loaded {len(df)} rows from {DATA_FILE}")


# ── Clean column names ─────────────────────────────────────────────────────────
# Some column names have trailing spaces from Excel — strip all of them
df.columns = df.columns.str.strip()


# ── Select only the columns needed for analysis ────────────────────────────────
df = df[[
    "Hatcheries",
    "Assay Type",
    "Larval Species Tested",
    "Water Type",
    "Filtered/Unfiltered",
    "Replicate",
    "Alive",
    "Dead",
    "Mortality"         # raw numeric % mortality (10 = 10%)
]]

# Rename to shorter, easier-to-type names
df.columns = [
    "hatchery",
    "assay_type",
    "species",
    "water_type",
    "filter_type",
    "replicate",
    "alive",
    "dead",
    "mortality"
]


# ── Remove empty rows ──────────────────────────────────────────────────────────
# Excel files often have blank rows at the bottom; drop them
df = df.dropna(subset=["hatchery", "mortality"])

# Make sure mortality is stored as a number, not a string
df["mortality"] = pd.to_numeric(df["mortality"], errors="coerce")

# Drop any rows where mortality could not be converted (e.g., "N/A" entries)
df = df.dropna(subset=["mortality"])

# Strip any extra whitespace from text columns so grouping works correctly
for col in ["hatchery", "assay_type", "water_type", "filter_type", "species"]:
    df[col] = df[col].str.strip()

print(f"After cleaning: {len(df)} rows")
print(f"Hatcheries:  {sorted(df['hatchery'].unique())}")
print(f"Assay types: {list(df['assay_type'].unique())}")
print(f"Water types: {list(df['water_type'].unique())}")
print(f"Filter types:{list(df['filter_type'].unique())}")


# ── Average mortality across the 3 replicates per treatment group ──────────────
# Each treatment (hatchery × assay type × species × water type × filter) was
# run in triplicate. We average those 3 replicates to get one value per treatment.
avg = df.groupby(
    ["hatchery", "assay_type", "species", "water_type", "filter_type"],
    as_index=False
)["mortality"].mean()

avg = avg.rename(columns={"mortality": "avg_mortality"})
avg["avg_mortality"] = avg["avg_mortality"].round(1)

# Add a simple True/False column indicating whether this treatment is flagged
avg["issue_detected"] = avg["avg_mortality"] > MORTALITY_THRESHOLD

print(f"\nAverage mortality computed for {len(avg)} treatment groups")


# ── Diagnosis: identify the most likely causative agent ───────────────────────
# For each hatchery × assay type × water type combination, find the most
# restrictive (smallest pore) filter that still shows mortality > threshold.
# That tells us the minimum size class of the causative agent.

diagnosis_rows = []  # collect one row of results per combination

for (hatchery, assay_type, species, water_type), group in avg.groupby(
        ["hatchery", "assay_type", "species", "water_type"]):

    # Build a lookup dictionary: filter_type -> avg_mortality
    filter_mort = dict(zip(group["filter_type"], group["avg_mortality"]))

    # Default assumption: no water quality issue
    likely_cause = "No water quality issue detected"
    flagged_filter = "None"

    # Work through filters from most restrictive (100 kDa) to least (Unfiltered)
    # The first filter we find with mortality > threshold is the diagnosis
    for f in reversed(FILTER_ORDER):
        if f in filter_mort and filter_mort[f] > MORTALITY_THRESHOLD:
            likely_cause = CAUSATIVE_AGENT[f]
            flagged_filter = f
            break  # stop at the most restrictive filter with an issue

    diagnosis_rows.append({
        "hatchery":       hatchery,
        "assay_type":     assay_type,
        "species":        species,
        "water_type":     water_type,
        "max_avg_mort":   round(group["avg_mortality"].max(), 1),
        "flagged_filter": flagged_filter,
        "likely_cause":   likely_cause,
    })

diagnosis_df = pd.DataFrame(diagnosis_rows)


# ── Acute vs. chronic comparison ──────────────────────────────────────────────
# If a hatchery shows NO issue in the acute assay but DOES show an issue in
# the chronic assay, the problem is likely chronic (husbandry or genetic),
# not driven by the water quality on a given day.

# Split the diagnosis table into acute and chronic
acute_df = diagnosis_df[diagnosis_df["assay_type"] == "Acute"][[
    "hatchery", "species", "water_type", "likely_cause"
]].rename(columns={"likely_cause": "acute_diagnosis"})

chronic_df = diagnosis_df[diagnosis_df["assay_type"] == "Chronic"][[
    "hatchery", "species", "water_type", "likely_cause"
]].rename(columns={"likely_cause": "chronic_diagnosis"})

# Merge so each row has both the acute and chronic result for a hatchery/water type
# outer join keeps hatcheries that only have one assay type
comparison = pd.merge(
    acute_df, chronic_df,
    on=["hatchery", "species", "water_type"],
    how="outer"
)

# Apply the interpretation logic to each row
def interpret_row(row):
    no_issue = "No water quality issue detected"

    # True if acute assay showed no problem (or wasn't run)
    acute_ok = pd.isna(row["acute_diagnosis"]) or row["acute_diagnosis"] == no_issue

    # True if chronic assay flagged an issue
    has_chronic = (
        not pd.isna(row["chronic_diagnosis"])
        and row["chronic_diagnosis"] != no_issue
    )

    if not acute_ok:
        return row["acute_diagnosis"]        # water quality issue found in acute
    elif has_chronic:
        return "Chronic, husbandry, or genetic issue"  # only shows in chronic
    else:
        return no_issue

comparison["final_interpretation"] = comparison.apply(interpret_row, axis=1)


# ── Save output tables ─────────────────────────────────────────────────────────
avg_out = os.path.join(TABLES_DIR, "avg_mortality_by_treatment.csv")
avg.to_csv(avg_out, index=False)
print(f"\nSaved table: {avg_out}")

diag_out = os.path.join(TABLES_DIR, "diagnosis_by_hatchery.csv")
diagnosis_df.to_csv(diag_out, index=False)
print(f"Saved table: {diag_out}")

comp_out = os.path.join(TABLES_DIR, "acute_vs_chronic_comparison.csv")
comparison.to_csv(comp_out, index=False)
print(f"Saved table: {comp_out}")


# ── Figure 1: Heatmaps — avg % mortality by hatchery and treatment ────────────
# One heatmap per assay type (Acute, Chronic)
# Rows = hatcheries, columns = water type + filter combination
# Color shows average % mortality; numbers are printed in each cell

for assay_type in sorted(avg["assay_type"].dropna().unique()):

    subset = avg[avg["assay_type"] == assay_type].copy()

    # Combine water type and filter into a single label for the column axis
    subset["treatment"] = subset["water_type"] + " | " + subset["filter_type"]

    # Pivot to a matrix so heatmap can be drawn
    pivot = subset.pivot_table(
        index="hatchery",
        columns="treatment",
        values="avg_mortality"
    )

    # Scale figure height with the number of hatcheries
    fig_height = max(5, len(pivot) * 0.45 + 2)

    fig, ax = plt.subplots(figsize=(16, fig_height))

    sns.heatmap(
        pivot,
        annot=True,          # print the value inside each cell
        fmt=".1f",           # one decimal place
        cmap="YlOrRd",       # yellow = low mortality, red = high mortality
        linewidths=0.4,      # thin grid lines between cells
        vmin=0, vmax=100,    # keep color scale fixed at 0–100%
        ax=ax,
        cbar_kws={"label": "Avg. % Mortality"}
    )

    ax.set_title(
        f"{assay_type} Assay — Average % Larval Mortality by Hatchery and Treatment\n"
        f"(values above {MORTALITY_THRESHOLD}% indicate a potential issue)",
        fontsize=12, pad=12
    )
    ax.set_xlabel("Water Source | Filter Type", fontsize=10)
    ax.set_ylabel("Hatchery", fontsize=10)
    ax.tick_params(axis="x", rotation=45)
    ax.tick_params(axis="y", rotation=0)

    # Add a descriptive figure caption below the heatmap
    # This follows academic convention: caption explains what is shown,
    # what the colors mean, and how to interpret the threshold
    fig.text(
        0.5, -0.02,
        f"Figure 1. Average percent larval mortality for {assay_type.lower()} assays across hatcheries and treatment types. "
        f"Cell color and value indicate average % mortality across 3 replicates. "
        f"Yellow = low mortality; red = high mortality (scale 0–100%). "
        f"Values above {MORTALITY_THRESHOLD}% indicate a potential water quality issue. "
        f"Columns show water source (Incoming, Tank, or Shed) combined with filter size "
        f"(Unfiltered, 10µm, 0.22µm, or 100 kDa).",
        ha="center", fontsize=9, style="italic", wrap=True
    )

    plt.tight_layout()

    outpath = os.path.join(FIGURES_DIR, f"heatmap_{assay_type.lower()}.png")
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure: {outpath}")


# ── Figure 2: Bar chart — max mortality per hatchery by assay type ────────────
# Shows the single highest average mortality observed across all treatments for
# each hatchery, split by assay type. Quickly highlights the most affected hatcheries.

max_mort = avg.groupby(
    ["hatchery", "assay_type"], as_index=False
)["avg_mortality"].max()

hatcheries = sorted(max_mort["hatchery"].unique())  # x-axis labels
assay_types = sorted(max_mort["assay_type"].dropna().unique())

bar_width = 0.35
colors = ["#4C72B0", "#DD8452"]  # blue = acute, orange = chronic

fig, ax = plt.subplots(figsize=(14, 5))

for i, at in enumerate(assay_types):
    subset = max_mort[max_mort["assay_type"] == at].set_index("hatchery")

    # Get max mortality for each hatchery (0 if hatchery not in this assay type)
    values = [
        subset.loc[h, "avg_mortality"] if h in subset.index else 0
        for h in hatcheries
    ]

    # Offset bars side-by-side
    bar_positions = [xi + i * bar_width for xi in range(len(hatcheries))]
    ax.bar(bar_positions, values, width=bar_width, label=at,
           color=colors[i], alpha=0.85)

# Horizontal dashed line at the 10% threshold
ax.axhline(MORTALITY_THRESHOLD, color="red", linestyle="--", linewidth=1.2,
           label=f"{MORTALITY_THRESHOLD}% threshold")

ax.set_xticks([xi + bar_width / 2 for xi in range(len(hatcheries))])
ax.set_xticklabels(hatcheries, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Max Avg. % Mortality")
ax.set_xlabel("Hatchery")
ax.set_title("Maximum Average Larval Mortality per Hatchery by Assay Type")
ax.legend()

# Add a descriptive figure caption below the bar chart
# Caption explains axes, bar colors, and the meaning of the threshold line
fig.text(
    0.5, -0.02,
    "Figure 2. Maximum average larval mortality per hatchery by assay type. "
    "Blue bars = acute assay (20–24 hr); orange bars = chronic assay (7 day). "
    "Each bar represents the highest average % mortality observed across all "
    "water source and filter combinations for that hatchery. "
    "Red dashed line indicates the 10% mortality threshold; hatcheries exceeding "
    "this threshold in acute assays indicate a water quality issue.",
    ha="center", fontsize=9, style="italic", wrap=True
)

plt.tight_layout()

bar_out = os.path.join(FIGURES_DIR, "max_mortality_by_hatchery.png")
fig.savefig(bar_out, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved figure: {bar_out}")


# ── Done ───────────────────────────────────────────────────────────────────────
print("\nAnalysis complete.")
print(f"  Figures -> {FIGURES_DIR}/")
print(f"  Tables  -> {TABLES_DIR}/")
