-- Ranked geographic investigation queue; minimum 100 observed deliveries.
WITH regions AS (
 SELECT state,COUNT(*) orders,SUM(late) late_orders,AVG(late)*100 late_pct,
 AVG(review_score) review_score,SUM(item_value) item_value
 FROM eligible GROUP BY state HAVING COUNT(*)>=100)
SELECT *,RANK() OVER(ORDER BY late_orders DESC) priority_rank FROM regions ORDER BY priority_rank;
