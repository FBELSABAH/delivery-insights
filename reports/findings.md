# Delivery investigation brief

Delivery Insights

DECISION BRIEF | Historical marketplace delivery investigations

1 / Investigate scale and reliability separately

SP recorded 1,820 late deliveries at 4.49%; RJ recorded 1,495 at 12.11%. Together they account for 50.7% of observed late deliveries. Start by comparing routes, sellers and delivery promises in these regions. Customer state alone cannot identify the responsible carrier or cause.

2 / Review the periods with elevated late rates

Among purchase months with at least 100 eligible deliveries, 2018-03 had the highest late rate: 18.96% across 7,003 orders. Compare its order mix, promises and operating conditions with adjacent months. Keep cohort follow-up consistent before judging later periods; the source ends in 2018.

3 / Examine the review association, then test explanations

Late deliveries averaged 2.27/5 versus 4.29/5 for on-time deliveries. Reviews cover 6,381/6,534 late and 89,443/89,936 on-time orders. These groups may differ in other ways; the score gap is not a causal effect or a forecast of improvement.

Data quality and measured technical results

The warehouse retained 99,441 orders and excluded 2,971 from delivery metrics. There were 2,965 missing actual delivery timestamps, including 8 delivered-status orders. No records were quarantined under the declared rules. Order grain and BRL item/freight totals reconcile exactly. All 3 full refreshes produced identical facts, metrics and exports (6.55-6.60s; local warm runs, download excluded).

Scope and next decision

Late means delivered calendar date after promised date. Review rows are averaged within each order before group comparison. Regional charts require 100 eligible orders. Validate the proposed investigations with an operations owner before recommending changes. No actual delivery reduction, cost saving or customer adoption has been demonstrated.

Source: Olist and collaborators, Brazilian E-Commerce Public Dataset (2016-2018), Kaggle. CC BY-NC-SA 4.0. Portfolio analysis; not commissioned by Olist. Runtime: Darwin arm64, Python 3.14.3. PostgreSQL 18; exact version in benchmark.json.
