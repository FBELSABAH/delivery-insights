"""Integration checks against the dedicated development warehouse, always rolled back."""
import os
import unittest
from warehouse import execute, query

@unittest.skipUnless(os.environ.get('DATABASE_URL'),'Set DATABASE_URL to run PostgreSQL integration tests')
class WarehouseIntegrity(unittest.TestCase):
 def setUp(self):
  self.dsn=os.environ['DATABASE_URL']

 def test_invalid_foreign_key_rolls_back_whole_transaction(self):
  before=query(self.dsn,'SELECT COUNT(*) n FROM delivery_insights.orders')[0]['n']
  with self.assertRaises(RuntimeError):
   execute(self.dsn,"BEGIN; DELETE FROM delivery_insights.order_reviews; INSERT INTO delivery_insights.order_items VALUES ('00000000000000000000000000000000',1,1,1); COMMIT;")
  self.assertEqual(query(self.dsn,'SELECT COUNT(*) n FROM delivery_insights.orders')[0]['n'],before)
  self.assertGreater(int(query(self.dsn,'SELECT COUNT(*) n FROM delivery_insights.order_reviews')[0]['n']),0)

 def test_fact_grain_and_exact_money_reconciliation(self):
  checks=query(self.dsn,"SELECT (SELECT COUNT(*) FROM delivery_insights.orders)=(SELECT COUNT(*) FROM delivery_insights.order_facts) grain_ok,(SELECT SUM(price) FROM delivery_insights.order_items)=(SELECT SUM(item_value) FROM delivery_insights.order_facts) money_ok")[0]
  self.assertEqual(checks,{'grain_ok':'t','money_ok':'t'})

 def test_calendar_day_and_preaggregated_children(self):
  sql="""BEGIN;
INSERT INTO delivery_insights.customers VALUES ('00000000000000000000000000000001','SP');
INSERT INTO delivery_insights.orders VALUES ('00000000000000000000000000000002','00000000000000000000000000000001','delivered','2018-01-01','2018-01-03 23:00','2018-01-03');
INSERT INTO delivery_insights.order_items VALUES ('00000000000000000000000000000002',1,10,1),('00000000000000000000000000000002',2,20,2);
INSERT INTO delivery_insights.order_reviews VALUES (-1,'00000000000000000000000000000003','00000000000000000000000000000002',2),(-2,'00000000000000000000000000000004','00000000000000000000000000000002',4);
COPY (SELECT item_value,review_score,late FROM delivery_insights.eligible WHERE order_id='00000000000000000000000000000002') TO STDOUT WITH CSV HEADER;
ROLLBACK;"""
  output=execute(self.dsn,sql)
  self.assertIn('30.00,3.0000000000000000,0',output)

if __name__=='__main__':unittest.main()
