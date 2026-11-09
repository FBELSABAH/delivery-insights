WITH months AS (SELECT month,COUNT(*) orders,AVG(late)*100 late_pct FROM eligible GROUP BY month)
SELECT *,late_pct-LAG(late_pct) OVER(ORDER BY month) change_percentage_points FROM months ORDER BY month;
