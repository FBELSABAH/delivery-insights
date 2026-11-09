# Delivery investigation brief

Observed 96,470 delivered orders with usable dates; 6,534 were late (6.77%). Excluded 2,971 orders from this metric.

First investigation region: SP, with 1,820 late deliveries. Prioritize by incident volume; the dashboard also shows rates to distinguish scale from reliability. Investigate carriers, routes and promises before changing operations.

Reviews by delivery outcome: [{"late": 0, "reviewed_orders": 89443, "average_score": 4.290589164793966}, {"late": 1, "reviewed_orders": 6381, "average_score": 2.2718225983388183}]. This is descriptive association, not a causal effect. Missing reviews may be selective.

Measured technical impact: automated ingestion, four-table reconciliation, ranked geographic analysis and month-over-month reporting in 2.633 seconds on this run. No revenue uplift or delivery improvement has been observed.

Historical 2016–2018 marketplace sample; no claim of current operating performance. Late means delivered calendar date after promised calendar date. Multiple reviews are averaged per order; missing reviews are excluded from review means. Item value excludes freight and is not profit.
