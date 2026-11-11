# Delivery Insights

Of 99,441 orders in the Olist dataset, 96,470 were delivered with usable dates. Of those, 6,534 arrived after the promised calendar date (6.77%). The SQL analysis ranks regions by late-order volume and tracks the late rate by month.

[Read the findings](reports/findings.md) · [Inspect the results and source counts](reports/results.json) · [See how the SQL defines an eligible order](sql/model.sql)

## Open the dashboard

Open [reports/dashboard.html](reports/dashboard.html) from a local copy of this repository. The report includes its data and works offline. The [regional](reports/regions.csv) and [monthly](reports/trends.csv) tables are also available as CSVs.

## Rebuild from the original data

Use Python 3.10 or later. Run these commands from the repository root. The download script retrieves the original Olist archive and verifies its checksum. If you already have that archive at `data/olist.zip`, start with `python3 run.py`.

```sh
python3 download.py
python3 run.py
python3 -m unittest discover -s tests
```

The build writes the SQLite warehouse to `data/analytics.sqlite` and regenerates the files in `reports/`. The tests use a small in-memory fixture and can run without the dataset.

## Architecture
CSV archive → typed SQL expressions over raw staging tables → one-row-per-order facts → eligible deliveries → regional rankings and monthly windows → dashboard and decision brief.

## Correctness
Aggregate item and review tables before joining; reconcile order counts and item values; reject duplicate primary keys. Eligibility requires delivered status and valid delivery/estimate dates. Late is measured in calendar days. Region is customer state; results do not establish seller or carrier responsibility. Rates use observed deliveries, not all orders. Regions require 100 observations. No claim of causal impact, production deployment or realized financial savings.

## Data and attribution
Olist and collaborators, Brazilian E-Commerce Public Dataset, historical 2016–2018 data. Obtain raw files from the original source and comply with its license (CC BY-NC-SA 4.0 as published by the source). Raw data are excluded from Git. Aggregated outputs retain source attribution. The archive checksum and row counts are recorded in reports/results.json. Rebuild timing is machine-dependent.

## Portfolio walkthrough
Explain why a many-to-many join inflates metrics; reproduce one regional calculation; explain LAG and RANK; discuss missing reviews and confounding. The project was developed with AI assistance; users should understand and extend it before claiming independent implementation expertise.
