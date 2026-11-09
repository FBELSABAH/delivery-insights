-- One row per order: aggregate one-to-many children BEFORE joining.
CREATE VIEW order_facts AS
WITH items AS (SELECT order_id, SUM(CAST(price AS REAL)) item_value, COUNT(*) item_count FROM order_items GROUP BY order_id),
reviews AS (SELECT order_id, AVG(CAST(review_score AS REAL)) review_score FROM order_reviews GROUP BY order_id)
SELECT o.order_id, c.customer_state state, substr(o.order_purchase_timestamp,1,7) month,
o.order_status, i.item_value,i.item_count,r.review_score,
CASE WHEN o.order_delivered_customer_date != '' AND o.order_estimated_delivery_date != '' THEN
julianday(date(o.order_delivered_customer_date))-julianday(date(o.order_estimated_delivery_date)) END delay_days
FROM orders o LEFT JOIN customers c USING(customer_id) LEFT JOIN items i USING(order_id) LEFT JOIN reviews r USING(order_id);
CREATE VIEW eligible AS SELECT *, CASE WHEN delay_days>0 THEN 1 ELSE 0 END late FROM order_facts WHERE order_status='delivered' AND delay_days IS NOT NULL;
