# Delivery investigation brief

Of 99,441 Olist orders, 96,470 were delivered with usable dates. **6,534 (6.77%) arrived late.** The rate excludes 2,971 orders. A delivery is late when it arrives after the promised calendar date.

## Where to investigate

Customer state **SP** had the most late deliveries (1,820). The regional table reports both the count and the rate for states with at least 100 eligible orders. High order volume can produce many late deliveries even when the rate is relatively low. [Compare states](regions.csv) or [see the monthly trend](trends.csv).

## What customers reported

| Delivery outcome | Orders with a review | Mean review score (out of 5) |
| --- | ---: | ---: |
| On time or early | 89,443 | 4.29 |
| Late | 6,381 | 2.27 |

Each reviewed order counts once. Multiple reviews for an order are averaged first. Orders without a review are excluded from the score averages, and customers who leave reviews may differ from those who do not. These historical observations cannot identify a carrier or explain what caused a rating.

[Metric definitions](../sql/model.sql) · [Source, row counts, and build results](results.json)
