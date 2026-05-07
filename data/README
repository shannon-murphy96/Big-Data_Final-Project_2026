About the BHHC:
In recent years, bivalve hatcheries in the Atlantic Coast of the USA have been affected by
larval crashes of unknown causes.  The Bivalve Hatchery Health Consortium (BHHC) was
established in 2023 to try to understand the causes leading to reduced larval performance
and identify avoidance and prevention tools.   A process was developed for enrollment of
hatcheries into the BHHC that protects confidentiality of their data and production practices. 
The BHHC also developed a protocol for the proactive collection of samples of water, algae,
and larvae from as many good and bad larval production runs as possible throughout the year.
As of September 2025, 37 (18 public-research-restoration and 19 commercial) hatcheries from the Atlantic
Coast of the USA have enrolled in the BHHC.  During the 2024 and 2025 production seasons, hatcheries
provided samples and data from more than 80 production runs (from 1 - 8 per hatchery). Sampling covered
four bivalve species (mainly eastern oysters, but also northern quahogs, bay scallops, and mussels).  
In 2024, 55% of the 33 production runs were crashes or showed low larval performance.  Most bad larval
runs showed failure of larvae to progress through development early in the run (by day 6 post
fertilization), commonly followed by crashes later in the production run. Histological examination
showed no evidence of known pathological conditions or infectious agents in larvae.  Water chemistry
analysis showed the presence of potentially toxic elements (e.g., arsenic) in only three of all production
runs. More than 500 bacterial isolates were cultured from both good and bad larval runs. Although a few
pathogenic vibrios were isolated, there was no consistent association of vibrios with bad runs, suggesting
vibriosis is not the primary cause of crashes. Molecular analysis of microbiota, however, showed that bad
runs can be predicted based on microbial composition.  Larval challenge experiments using water from larval
performance runs suggests that some of these issues could be due to a virus or a toxin/s able to pass through
a 0.22-micron filter. Current efforts are focused on toxin (e.g., from algal blooms) and toxicant (anthropogenic
chemicals) identification.  Results from the 2024 season suggest that the issues affecting larval production
are complex, confirming the need for a collaborative, integrated approach to identify and solve the
issues.

This research is funded by the USDA Northeast Regional Aquaculture Center Award 123476-Z5220211

About the Experiment:
The BHHC has developed a screening assay using healthy
larvae exposed to hatchery-collected samples to identify the type of disease-causing agents
that could be present in the water or larvae from hatcheries experiencing low larval
performance.During the 2024 and 2025 seasons, the BHHC hatcheries proactively collected incoming
water (before treatment), tank water, and larval samples at different time points in at least
two production runs. Live larvae from early during the production run (1 - 5 days post
fertilization) were shipped overnight to our laboratory, washed, and incubated in filtered
sterile artificial seawater (FSSW) overnight to allow the shedding of infectious agents to the
water (shed water). At the end of the production run, hatcheries reported the quality of the
run (from 0 - total loss, to 3 - normal run). Screening assays were developed to identify the
source and type of agent leading to low larval performance. Incoming, tank, and shed water
were size fractionated and the fractions were used in larval assays
to identify which size fractions retain pathogenic effects. Healthy larvae or hemocytes were
exposed to FSSW (negative control), the non fractionated sample water, 10 micron-filtered
water (eliminating protozoan and metazoan parasites), 0.22 micron-filtered water
(eliminating bacteria), and 50 kDa-filtered water (eliminating viruses and retaining toxins
and small molecules). These assays replicated clinical signs observed in larvae from
hatchery crashes, indicating their potential to guide the process of identification of causes
of these larval crashes. 


This Script:
The analysis.py script allows one to upload the mortality results from a larval assay and tease apart
the pathology of hatchery run. Note that hatcheries runs are identified using their anonymous codes 
and which number run is being analyzed, for example S3W-R2 refers to hatchery code S3W and the second run of
samples they've provided. 

The following columns need to be present when uploading a spreadsheet:
 - Hatcheries
 - Assay Type
 - Larval Species Tested
 - Water Type
 - Filtered/Unfiltered
 - Replicate
 - Alive
 - Dead
 - Mortality

The contents of those columns should be the following:
 - Hatcheries — hatchery and run code (e.g., B47-R1, RRD-R2)
 - Assay Type — Acute (20-24hr assay)  or Chronic (7 day) 
 - Larval Species Tested — species name (e.g., Crassostrea virginica, Mercenaria mercenaria)
 - Water Type — Incoming Water, Tank Water, or Shed Water
 - Filtered/Unfiltered — Unfiltered, 10um filter, 0.22um filter, or 100 kDa filter
 - Replicate — 1, 2, or 3 
 - Alive — count of live larvae at end of assay
 - Dead — count of dead larvae at end of assay
 - Mortality — raw % mortality as a number (10 means 10%)
 Everything else in the spreadsheet is ignored.

Summary of the outputs:
Tables
- avg_mortality_by_treatment.csv —  one row per hatchery × assay type × species × water type × filter combination,
  showing the average % mortality across the 3 replicates and whether it exceeds the 10% threshold
- diagnosis_by_hatchery.csv — one row per hatchery × assay type × water type, showing the highest average mortality
  observed and the likely causative agent based on the smallest filter that still showed mortality
- acute_vs_chronic_comparison.csv — compares acute and chronic results side by side and flags combinations where no acute
  issue was found but a chronic issue was, indicating a chronic/husbandry/genetic problem rather than a water quality issue

Figures
- heatmap_acute.png — grid of all hatcheries (rows) vs. all water type + filter treatments (columns) with cell color and
  number showing average % mortality for acute assays. makes it easy to spot which hatcheries and treatments are
  problematic
- heatmap_chronic.png — same as above but for chronic assays
- max_mortality_by_hatchery.png — bar chart showing the single highest average mortality recorded per hatchery, with
  acute and chronic bars side by side and a red dashed line at the 10% threshold

AI usage:
Claude was used a a tool for opimizing code to remove bugs, and for all graphing. Graphs were created by prompting
Claude with an example spreadsheet and expalining the goals. Claude assisted with breaking down this code so it could 
be adjusted by me. When removing bugs, the script would be pasted into Claude which would then suggest ideas for bug 
fixes. Code for filtering and calculating averages from triplicates was created using instruction from
Dr. Rachel Schwartz's BIO539 course powerpoints and assignments as well as readings from the following:
- A Whirlwind Tour of Python. Jake VanderPlas. 2016.
- Python Data Science. Jake VanderPlas. 2017. O’Reilly Media.
