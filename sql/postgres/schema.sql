-- Dedicated portfolio schema. Refreshes never touch objects outside this schema.
CREATE SCHEMA IF NOT EXISTS delivery_insights;
SET search_path TO delivery_insights;
CREATE TABLE IF NOT EXISTS customers (
 customer_id text PRIMARY KEY CHECK (customer_id ~ '^[0-9a-f]{32}$'),
 customer_state char(2) NOT NULL CHECK (customer_state ~ '^[A-Z]{2}$')
);
CREATE TABLE IF NOT EXISTS orders (
 order_id text PRIMARY KEY CHECK (order_id ~ '^[0-9a-f]{32}$'),
 customer_id text NOT NULL REFERENCES customers,
 order_status text NOT NULL CHECK(order_status IN ('created','approved','invoiced','processing','shipped','delivered','unavailable','canceled')),
 purchased_at timestamp NOT NULL, delivered_at timestamp, estimated_at timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
 order_id text NOT NULL REFERENCES orders, order_item_id integer NOT NULL CHECK(order_item_id > 0),
 price numeric(14,2) NOT NULL CHECK(price >= 0), freight_value numeric(14,2) NOT NULL CHECK(freight_value >= 0),
 PRIMARY KEY(order_id, order_item_id)
);
CREATE TABLE IF NOT EXISTS order_reviews (
 source_row integer PRIMARY KEY, review_id text NOT NULL, order_id text NOT NULL REFERENCES orders,
 review_score smallint NOT NULL CHECK(review_score BETWEEN 1 AND 5)
);
CREATE INDEX IF NOT EXISTS orders_customer_idx ON orders(customer_id);
CREATE INDEX IF NOT EXISTS reviews_order_idx ON order_reviews(order_id);
CREATE OR REPLACE VIEW order_facts AS
WITH items AS (SELECT order_id, SUM(price) item_value, SUM(freight_value) freight_value, COUNT(*) item_count FROM order_items GROUP BY order_id),
reviews AS (SELECT order_id, AVG(review_score)::numeric review_score, COUNT(*) review_count FROM order_reviews GROUP BY order_id)
SELECT o.order_id, c.customer_state::text state, date_trunc('month', o.purchased_at)::date AS month,
 o.order_status, o.purchased_at, o.delivered_at, o.estimated_at,
 i.item_value, i.freight_value, COALESCE(i.item_count,0) item_count,
 r.review_score, COALESCE(r.review_count,0) review_count,
 o.delivered_at::date - o.estimated_at::date delay_days
FROM orders o LEFT JOIN customers c USING(customer_id)
LEFT JOIN items i USING(order_id) LEFT JOIN reviews r USING(order_id);
CREATE OR REPLACE VIEW eligible AS
SELECT *, CASE WHEN delay_days>0 THEN 1 ELSE 0 END late
FROM order_facts WHERE order_status='delivered' AND delay_days IS NOT NULL;
CREATE OR REPLACE VIEW regional_metrics AS
SELECT state,COUNT(*) orders,SUM(late) late_orders,
 ROUND(AVG(late)*100,6) late_pct, ROUND(AVG(review_score),6) average_review_score,
 SUM(item_value) item_value,
 RANK() OVER(ORDER BY SUM(late) DESC) priority_rank
FROM eligible GROUP BY state HAVING COUNT(*) >= 100;
CREATE OR REPLACE VIEW monthly_metrics AS
WITH months AS (SELECT month,COUNT(*) orders,SUM(late) late_orders,AVG(late)*100 late_pct FROM eligible GROUP BY month)
SELECT month,orders,late_orders,ROUND(late_pct,6) late_pct,
 ROUND(late_pct-LAG(late_pct) OVER(ORDER BY month),6) change_percentage_points,
 orders >= 100 AS sufficient_volume
FROM months;
COMMENT ON VIEW order_facts IS 'One row per accepted order; child tables are aggregated before joining. BRL item value excludes freight.';
COMMENT ON VIEW eligible IS 'Delivered status and non-null actual/estimated timestamps. Late compares calendar dates, not hours. Not a causal estimate.';
