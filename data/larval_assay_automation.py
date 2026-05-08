#!/usr/bin/env python3

# larval_assay_automation.py
# Analyzes shellfish hatchery larval bioassay results to identify causative agents of crashes and where they're being introduced
# Research Question: Where do water quality issues arise in shellfish hatcheries
# (incoming water or tank water), and what is the likely causative
# agent based on which filter size still allows larval mortality to occur?
# Usage: python larval_assay_automation.py [data file]
# Example: python larval_assay_automation.py data/BHHC_data.csv
# Output: figures/ (heatmaps and bar chart) and tables/ (summary CSVs)

"""
Filter interpretation key — each filter removes progressively smaller agents,
so mortality persisting through a smaller filter tells us what size class the
causative agent belongs to:
    Unfiltered       -> parasite, bacteria, virus, toxin, or pollutant
    10um filter      -> bacteria, virus, toxin, or pollutant  (parasites removed)
    0.22um filter    -> virus, toxin, or pollutant            (bacteria removed)
    100 kDa filter   -> toxin or pollutant only               (viruses removed)

A treatment is flagged if average % mortality across the 3 replicates exceeds
10%. Comparing acute (20-24hr) and chronic (7 day) assay results helps us
distinguish an acute water quality event from a chronic/husbandry/genetic problem.

Usage:
    python larval_assay_automation.py <path_to_data_file>   # pass file path directly
    python larval_assay_automation.py                        # will prompt you to enter the path

Example:
    python larval_assay_automation.py data/BHHC_data.csv
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# Starting by figuring out where the data file is coming from
# Either the user passes it in on the command line or we ask them for it
# This way anyone can run it without knowing command line syntax
if len(sys.argv) == 2:
    DATA_FILE = sys.argv[1]  # they gave us the path already, use it
else:
    # no argument given so lets just ask them to type the path in
    DATA_FILE = input("Enter path to data file (e.g. data/BHHC_data.csv): ").strip()

# make sure the file actually exists before we try to do anything with it
# otherwise python gives a confusing error message so this is friendlier
if not os.path.exists(DATA_FILE):
    print(f"Error: file not found: {DATA_FILE}")
    print("Please check the path and try again.")
    sys.exit(1)


# setting up the output folders for figures and tables
# using relative paths so this works on anyones computer, not just mine
FIGURES_DIR = "figures"
TABLES_DIR = "tables"

# create the folders if they dont exist yet, exist_ok means it wont crash if they already do
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(TABLES_DIR, exist_ok=True)


# 10% is our cutoff for flagging a treatment as having an issue
# anything above this is considered biologically meaningful mortality
MORTALITY_THRESHOLD = 10

# filter sizes from largest pore to smallest — order matters here because
# later we work through this list in reverse to find the most restrictive
# filter that still shows mortality, which tells us the size of the agent
FILTER_ORDER = ["Unfiltered", "10um filter", "0.22um filter", "100 kDa filter"]

# what agent could still be causing mortality at each filter level
# based on what is small enough to pass through that filter
CAUSATIVE_AGENT = {
    "Unfiltered":     "Parasite, bacteria, virus, toxin, or pollutant",
    "10um filter":    "Bacteria, virus, toxin, or pollutant",
    "0.22um filter":  "Virus, toxin, or pollutant",
    "100 kDa filter": "Toxin or pollutant",
}


# loading the data file — the CSV has an extra summary table tacked on to the right
# so we only read the first 18 columns to avoid pulling in that junk
df = pd.read_csv(DATA_FILE, usecols=range(18))

print(f"Loaded {len(df)} rows from {DATA_FILE}")


# column names sometimes come in with trailing spaces from excel, strip those off
# otherwise the groupby steps later will fail in a confusing way
df.columns = df.columns.str.strip()


# pulling out only the columns we actually need for the analysis
# everything else in the spreadsheet gets ignored
df = df[[
    "Hatcheries",
    "Assay Type",
    "Larval Species Tested",
    "Water Type",
    "Filtered/Unfiltered",
    "Replicate",
    "Alive",
    "Dead",
    "Mortality"         # raw numeric % mortality, so 10 means 10%
]]

# renaming to shorter names so theyre easier to type throughout the rest of the script
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


# dropping empty rows — excel files almost always have blank rows at the bottom
# and we cant do math on empty cells so they have to go
df = df.dropna(subset=["hatchery", "mortality"])

# making sure mortality is a number and not a string, coerce turns anything
# that cant be converted (like "N/A") into NaN so we can drop those too
df["mortality"] = pd.to_numeric(df["mortality"], errors="coerce")
df = df.dropna(subset=["mortality"])

# stripping whitespace from text columns so grouping works correctly
# a space at the end of "Acute " would make it look like a different group than "Acute"
for col in ["hatchery", "assay_type", "water_type", "filter_type", "species"]:
    df[col] = df[col].str.strip()

print(f"After cleaning: {len(df)} rows")
print(f"Hatcheries:  {sorted(df['hatchery'].unique())}")
print(f"Assay types: {list(df['assay_type'].unique())}")
print(f"Water types: {list(df['water_type'].unique())}")
print(f"Filter types:{list(df['filter_type'].unique())}")


# averaging the 3 replicates per treatment group
# each treatment was run in triplicate so we collapse those down to one average value
# grouping by all the identifying columns so each unique combination gets its own row
avg = df.groupby(
    ["hatchery", "assay_type", "species", "water_type", "filter_type"],
    as_index=False
)["mortality"].mean()

avg = avg.rename(columns={"mortality": "avg_mortality"})
avg["avg_mortality"] = avg["avg_mortality"].round(1)

# flagging any treatment where average mortality exceeds our 10% threshold
avg["issue_detected"] = avg["avg_mortality"] > MORTALITY_THRESHOLD

print(f"\nAverage mortality computed for {len(avg)} treatment groups")


# diagnosis step — figuring out the most likely causative agent for each hatchery run
# the logic here is: work through filters from smallest pore to largest and find
# the most restrictive one that still shows mortality above the threshold
# that tells us the smallest size class the agent could belong to
diagnosis_rows = []

for (hatchery, assay_type, species, water_type), group in avg.groupby(
        ["hatchery", "assay_type", "species", "water_type"]):

    # build a quick lookup of filter type to average mortality for this group
    filter_mort = dict(zip(group["filter_type"], group["avg_mortality"]))

    # start by assuming no issue until we find one
    likely_cause = "No water quality issue detected"
    flagged_filter = "None"

    # go through filters from most restrictive to least and stop at the first one
    # that shows mortality — thats the smallest thing that could be causing it
    for f in reversed(FILTER_ORDER):
        if f in filter_mort and filter_mort[f] > MORTALITY_THRESHOLD:
            likely_cause = CAUSATIVE_AGENT[f]
            flagged_filter = f
            break  # found our answer, stop looking

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


# comparing acute vs chronic results to separate water quality issues from
# chronic problems like husbandry or genetics
# if a hatchery only shows up as an issue in the chronic assay but not the acute,
# thats a sign the problem isnt in the water on that particular day

# split into separate acute and chronic tables first
acute_df = diagnosis_df[diagnosis_df["assay_type"] == "Acute"][[
    "hatchery", "species", "water_type", "likely_cause"
]].rename(columns={"likely_cause": "acute_diagnosis"})

chronic_df = diagnosis_df[diagnosis_df["assay_type"] == "Chronic"][[
    "hatchery", "species", "water_type", "likely_cause"
]].rename(columns={"likely_cause": "chronic_diagnosis"})

# merge them together so each row has both results side by side
# outer join keeps hatcheries that only have one assay type so we dont lose anyone
comparison = pd.merge(
    acute_df, chronic_df,
    on=["hatchery", "species", "water_type"],
    how="outer"
)

# apply the interpretation logic row by row
def interpret_row(row):
    no_issue = "No water quality issue detected"

    # was there a problem in the acute assay or was it clean
    acute_ok = pd.isna(row["acute_diagnosis"]) or row["acute_diagnosis"] == no_issue

    # did the chronic assay flag something
    has_chronic = (
        not pd.isna(row["chronic_diagnosis"])
        and row["chronic_diagnosis"] != no_issue
    )

    if not acute_ok:
        return row["acute_diagnosis"]        # acute issue found, report it
    elif has_chronic:
        return "Chronic, husbandry, or genetic issue"  # only chronic, flag it differently
    else:
        return no_issue  # all clear

comparison["final_interpretation"] = comparison.apply(interpret_row, axis=1)


# saving all three tables out to the tables folder
avg_out = os.path.join(TABLES_DIR, "avg_mortality_by_treatment.csv")
avg.to_csv(avg_out, index=False)
print(f"\nSaved table: {avg_out}")

diag_out = os.path.join(TABLES_DIR, "diagnosis_by_hatchery.csv")
diagnosis_df.to_csv(diag_out, index=False)
print(f"Saved table: {diag_out}")

comp_out = os.path.join(TABLES_DIR, "acute_vs_chronic_comparison.csv")
comparison.to_csv(comp_out, index=False)
print(f"Saved table: {comp_out}")


# Figure 1 — heatmaps showing average mortality by hatchery and treatment
# making one heatmap for acute and one for chronic so they dont get jumbled together
# rows are hatcheries, columns are water type + filter combo, color shows mortality level

for assay_type in sorted(avg["assay_type"].dropna().unique()):

    subset = avg[avg["assay_type"] == assay_type].copy()

    # combining water type and filter into one label for the column axis
    subset["treatment"] = subset["water_type"] + " | " + subset["filter_type"]

    # pivot into a matrix format so seaborn can draw the heatmap
    pivot = subset.pivot_table(
        index="hatchery",
        columns="treatment",
        values="avg_mortality"
    )

    # scale the figure height based on how many hatcheries we have
    # so it doesnt get too squished if theres a lot of them
    fig_height = max(5, len(pivot) * 0.45 + 2)

    fig, ax = plt.subplots(figsize=(16, fig_height))

    sns.heatmap(
        pivot,
        annot=True,          # print the actual number in each cell
        fmt=".1f",           # one decimal place is enough
        cmap="YlOrRd",       # yellow = low mortality, red = high mortality
        linewidths=0.4,      # thin lines between cells so its easier to read
        vmin=0, vmax=100,    # fix the color scale so both heatmaps are comparable
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

    # academic figure caption below the heatmap explaining what everything means
    fig.text(
        0.5, -0.02,
        f"Figure 1. Average percent larval mortality for {assay_type.lower()} assays across hatcheries and treatment types. "
        f"Cell color and value indicate average % mortality across 3 replicates. "
        f"Yellow = low mortality; red = high mortality (scale 0-100%). "
        f"Values above {MORTALITY_THRESHOLD}% indicate a potential water quality issue. "
        f"Columns show water source (Incoming, Tank, or Shed) combined with filter size "
        f"(Unfiltered, 10um, 0.22um, or 100 kDa).",
        ha="center", fontsize=9, style="italic", wrap=True
    )

    plt.tight_layout()

    outpath = os.path.join(FIGURES_DIR, f"heatmap_{assay_type.lower()}.png")
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure: {outpath}")


# Figure 2 — bar chart showing the single highest mortality per hatchery
# good for a quick overview of which hatcheries are most affected
# acute and chronic bars side by side so you can compare at a glance

max_mort = avg.groupby(
    ["hatchery", "assay_type"], as_index=False
)["avg_mortality"].max()

hatcheries = sorted(max_mort["hatchery"].unique())  # x axis
assay_types = sorted(max_mort["assay_type"].dropna().unique())

bar_width = 0.35
colors = ["#4C72B0", "#DD8452"]  # blue for acute, orange for chronic

fig, ax = plt.subplots(figsize=(14, 5))

for i, at in enumerate(assay_types):
    subset = max_mort[max_mort["assay_type"] == at].set_index("hatchery")

    # get max mortality for each hatchery, use 0 if that hatchery didnt run this assay type
    values = [
        subset.loc[h, "avg_mortality"] if h in subset.index else 0
        for h in hatcheries
    ]

    # offset the bars so acute and chronic sit next to each other per hatchery
    bar_positions = [xi + i * bar_width for xi in range(len(hatcheries))]
    ax.bar(bar_positions, values, width=bar_width, label=at,
           color=colors[i], alpha=0.85)

# red dashed line at 10% so its easy to see who crossed the threshold
ax.axhline(MORTALITY_THRESHOLD, color="red", linestyle="--", linewidth=1.2,
           label=f"{MORTALITY_THRESHOLD}% threshold")

ax.set_xticks([xi + bar_width / 2 for xi in range(len(hatcheries))])
ax.set_xticklabels(hatcheries, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Max Avg. % Mortality")
ax.set_xlabel("Hatchery")
ax.set_title("Maximum Average Larval Mortality per Hatchery by Assay Type")
ax.legend()

# academic figure caption explaining the bars and threshold line
fig.text(
    0.5, -0.02,
    "Figure 2. Maximum average larval mortality per hatchery by assay type. "
    "Blue bars = acute assay (20-24 hr); orange bars = chronic assay (7 day). "
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


# all done! figures and tables should be in their folders
print("\nAnalysis complete.")
print(f"  Figures -> {FIGURES_DIR}/")
print(f"  Tables  -> {TABLES_DIR}/")
