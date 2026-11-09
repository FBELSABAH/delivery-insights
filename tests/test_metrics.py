import unittest,sqlite3
from pathlib import Path
class Metrics(unittest.TestCase):
 def test_many_to_many_and_calendar_day(self):
  d=sqlite3.connect(':memory:')
  d.executescript("""CREATE TABLE orders(order_id,customer_id,order_purchase_timestamp,order_status,order_delivered_customer_date,order_estimated_delivery_date);CREATE TABLE customers(customer_id,customer_state);CREATE TABLE order_items(order_id,price);CREATE TABLE order_reviews(order_id,review_score);INSERT INTO orders VALUES('a','c','2018-01-01','delivered','2018-01-03 23:00:00','2018-01-03 00:00:00'),('b','c','2018-01-01','delivered','','2018-01-03');INSERT INTO customers VALUES('c','SP');INSERT INTO order_items VALUES('a','10'),('a','20');INSERT INTO order_reviews VALUES('a','2'),('a','4');""")
  d.executescript((Path(__file__).parents[1]/'sql/model.sql').read_text())
  self.assertEqual(d.execute('SELECT COUNT(*) FROM order_facts').fetchone()[0],2)
  self.assertEqual(d.execute('SELECT item_value,review_score,late FROM eligible').fetchone(),(30.0,3.0,0))
  self.assertEqual(d.execute('SELECT COUNT(*) FROM eligible').fetchone()[0],1)
if __name__=='__main__':unittest.main()
