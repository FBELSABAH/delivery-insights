# Data-quality report

Generated from the pinned archive during the PostgreSQL build. Quarantine counts are observed, not planted demo defects.

| Source | Read | Accepted | Quarantined | Duplicate keys | Exact duplicates |
|---|---:|---:|---:|---:|---:|
| customers | 99,441 | 99,441 | 0 | 0 | 0 |
| orders | 99,441 | 99,441 | 0 | 0 | 0 |
| order_items | 112,650 | 112,650 | 0 | 0 | 0 |
| order_reviews | 99,224 | 99,224 | 0 | 0 | 0 |

## Missing source values

These counts cover every original source column, including columns not loaded into the warehouse. Optional empty fields are not automatically errors.

### customers


### orders

- order_approved_at: 160
- order_delivered_carrier_date: 1,783
- order_delivered_customer_date: 2,965

### order_items


### order_reviews

- review_comment_message: 58,274
- review_comment_title: 87,658

Repeated review-ID rows: 814. Review IDs are not unique in this source; these rows are preserved, not mislabeled as duplicate primary keys.

## Fact diagnostics

- missing_delivery_timestamp: 2,965
- delivered_without_timestamp: 8
- delivery_before_purchase: 0
- orders_without_items: 775
- orders_without_reviews: 768

## Reconciliation

- One-row-per-order check: PASS (99,441 facts).
- Item and freight totals: exact NUMERIC equality, checked inside the load transaction before commit.
- Parent/child references and primary keys: enforced by PostgreSQL constraints.
- Orders without delivery timestamps remain in facts, but are excluded from delivery-rate denominators.
- Multiple review rows are averaged per order before computing group means. Review ID alone is not treated as unique.
- Missing optional source fields, including review text, do not cause record rejection.

## Quarantine policy

First valid primary-key row wins; subsequent duplicate keys quarantined. Reviews preserve source-row grain. Empty optional delivered timestamps remain null.
Rejected source row numbers and reasons are in rejected_records.csv; review comments and personal free text are never exported.
File-level header/CSV failures abort the build. A failed database transaction rolls back the refresh.

## Scope

Only the four required tables are validated. This is not an audit of every Olist dataset. First-valid-row duplicate handling is deterministic, but a production system would require business approval before resolving conflicting duplicates.
The source contains historical marketplace data, not current PEI operating data. No patient data are used.
