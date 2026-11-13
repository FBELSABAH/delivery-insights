# Delivery Insights

**Which delivery problems should an operations team investigate first?** A reproducible PostgreSQL analytics project using 99,441 historical Olist marketplace orders: source validation, exact reconciliation, replay measurements and a native Tableau decision dashboard.

This is a portfolio case study, not work commissioned by Olist or a PEI employer. Results describe a 2016-2018 Brazilian marketplace snapshot, not current operating performance.

Of the 99,441 source orders, 96,470 are eligible for delivery analysis; 6,534 were late (6.77%). [Inspect the SQL definitions](sql/postgres/schema.sql) or [read the findings](reports/findings.md).

## Explore

- [One-page decision brief](reports/decision_brief.pdf): findings, proposed investigations, limitations and measured technical results.
- [Packaged Tableau workbook](tableau/Delivery_Insights.twbx): self-contained dashboard answering three operational questions.
- [Data-quality report](reports/data_quality.md) and [machine-readable audit](reports/data_quality.json).
- [Three-run benchmark](reports/benchmark.json): measured timings and stable-output checks, with environment details.
- [Schema and metric contracts](docs/schema.md): grain, keys, ER diagram and refresh behavior.

## Three questions

1. **Where should we investigate first?** Compare regional late-delivery counts and late rates. Scale and reliability are different.
2. **When did reliability change?** Examine purchase-month late rates alongside order volumes. Low-volume periods and incomplete follow-up require caution.
3. **How do reviews differ by delivery outcome?** Compare average order-level scores and review coverage. This is association, not evidence that lateness caused the difference.

## Reproduce with PostgreSQL

Requires Python 3.10+, PostgreSQL 18 client tools (`psql`) and a PostgreSQL server. The core pipeline uses only Python's standard library. Tableau is needed to open/edit the workbook, not to rebuild the warehouse.

```sh
python3 download.py
cp .env.example .env
# Choose a local password in .env; it is ignored by Git.
docker compose up -d --wait
set -a
. ./.env
set +a
python3 warehouse.py
python3 warehouse.py --benchmark 3
python3 -m unittest discover -s tests -v
```

With an existing local PostgreSQL instance, create a dedicated development database and set `DATABASE_URL` to its connection string instead of using Docker. The pipeline refreshes only its `delivery_insights` schema; do not use a production database. Set `PSQL` if the executable is not on PATH. The Docker example binds to localhost and requires a password. Stop it with `docker compose down` when finished; the named volume is preserved.

## Architecture

```text
Pinned original ZIP -> source validation + quarantine reasons
 -> typed PostgreSQL tables with keys, references and value checks
 -> preaggregated children -> one-row-per-order facts
 -> exact order / item-value / freight reconciliation
 -> regional ranks, monthly windows, review comparison
 -> Tableau aggregates + quality report + benchmark + decision brief
```

An empty optional delivery timestamp remains null and is excluded from delivery-rate denominators. Invalid required fields and orphan references are quarantined. Multiple legitimate reviews are retained and averaged before joining. The transactional full refresh prevents replayed imports from doubling totals. Duplicate handling is deterministic, but a production system would need business approval to resolve conflicting records.

## Tableau and report refresh

The workbook contains aggregates only, without customer/order identifiers or free-text reviews. Source aggregates are exported as `reports/tableau_metrics.csv`. See [Tableau documentation](tableau/README.md) for chart definitions, packaging and refresh instructions.

`python3 make_brief.py` regenerates the PDF after a successful warehouse benchmark (optional dependency: ReportLab). Every reported value comes from measured outputs. Three local full imports are a replay/repeatability benchmark, not a production concurrency or scalability test. Download time is excluded.

## Verification

Unit tests exercise invalid money/timestamps, duplicates, orphan references, missing values and repeated review IDs. With `DATABASE_URL` set, integration tests verify PostgreSQL calendar-day logic, preaggregation, exact reconciliation and rollback after a foreign-key failure. Synthetic test defects are not reported as defects found in the original archive.

The original offline HTML dashboard remains available at `reports/dashboard.html`. The original SQLite demonstration remains available through `python3 run.py`; it writes to `reports/legacy/` so it cannot overwrite PostgreSQL outputs.

## Attribution and limits

Olist and collaborators, [Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), historical 2016-2018 data. Source license: CC BY-NC-SA 4.0 as published by the provider. Raw files are excluded from Git. Derived reports and workbook aggregates retain source attribution and noncommercial/share-alike restrictions; no unrestricted commercial-data license is implied.

No delivery improvement, revenue uplift, clinical result or customer adoption has been observed. Technical measurements are distinct from potential business usefulness. Developed with AI assistance; contributors should understand and extend the implementation before claiming independent expertise.
