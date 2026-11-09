# Delivery Insights
An order-level analytics case study for prioritizing delivery investigations using real Olist marketplace data.

## Run
Python 3.10+; no dependencies. Download the original dataset from https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce into `data/olist.zip`, then run:
```
python3 download.py  # fetch and verify the pinned original archive
python3 run.py
python3 -m unittest discover -s tests
```
Open `reports/dashboard.html`. This dashboard works offline. Review `reports/findings.md` and the SQL source. Outputs include a SQLite warehouse and CSV exports suitable for Tableau. A native Tableau workbook is not included.

## Architecture
CSV archive → typed SQL expressions over raw staging tables → one-row-per-order facts → eligible deliveries → regional rankings and monthly windows → dashboard and decision brief.

## Correctness
Aggregate item and review tables before joining; reconcile order counts and item values; reject duplicate primary keys. Eligibility requires delivered status and valid delivery/estimate dates. Late is measured in calendar days. Region is customer state; results do not establish seller or carrier responsibility. Rates use observed deliveries, not all orders. Regions require 100 observations. No claim of causal impact, production deployment or realized financial savings.

## Data and attribution
Olist and collaborators, Brazilian E-Commerce Public Dataset, historical 2016–2018 data. Obtain raw files from the original source and comply with its license (CC BY-NC-SA 4.0 as published by the source). Raw data are excluded from Git. Aggregated outputs retain source attribution. The archive checksum and row counts are recorded in reports/results.json. Rebuild timing is machine-dependent.

## Portfolio walkthrough
Explain why a many-to-many join inflates metrics; reproduce one regional calculation; explain LAG and RANK; discuss missing reviews and confounding. The project was developed with AI assistance; users should understand and extend it before claiming independent implementation expertise.
