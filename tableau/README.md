# Tableau operations review

Open `Delivery_Insights.twbx` in Tableau Public/Desktop 2026.2 or later. The package includes a native Hyper extract and aggregate CSV; no server credentials or raw order/customer identifiers are required. It is a local workbook, not a publicly published visualization.

## Views

- **1a: Late deliveries by customer state**: SUM(late_orders), top 10 states ranked by late-delivery volume, minimum 100 eligible orders. Labels include investigation rank.
- **1b: Late rate by customer state**: AVG(late_pct), the same 10 investigation states (not the 10 highest rates). One row per state makes AVG a safe display aggregation; do not sum rates across regions.
- **2: Monthly late rate**: chronological YYYY-MM labels, monthly rows only, orders >= 100. Hover for volume. Full unfiltered monthly exports remain in reports/trends.csv.
- **3: Review scores by outcome**: AVG(average_review_score), review-comparison rows only. Hover includes eligible and reviewed orders. Each row is an order-level group mean, not a count-weighted mean of raw reviews.

A `question` filter on each sheet prevents mixing different grains in the aggregate source. Do not total the entire CSV: regional, monthly and review groups describe overlapping populations. The dashboard includes metric definitions and interpretation limits. Monthly rates are observational and affected by incomplete follow-up near the source snapshot's end.

## Refresh

1. Run `python3 warehouse.py --benchmark 3` to validate and export fresh metrics.
2. Open the unpackaged TWB in Tableau. If prompted, locate `Data/tableau_metrics.csv` (replace it with reports/tableau_metrics.csv after a data change).
3. Refresh/recreate the extract and save a packaged workbook. Verify all four sheets against the CSVs.
4. Regenerate the PDF brief with `python3 make_brief.py`.

The Python workbook builder accepts a Tableau-created TWB that already contains a matching Hyper extract. It does not update Hyper automatically; re-export the template from Tableau after source changes. The current packaged extract is from the measured committed source snapshot.

Source: Olist and collaborators, Brazilian E-Commerce Public Dataset, https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce . Historical 2016-2018; CC BY-NC-SA 4.0. No current PEI or patient data.
