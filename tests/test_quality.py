import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from quality import prepare, money, timestamp

A='a'*32; B='b'*32; C='c'*32

class SourceValidation(unittest.TestCase):
 def test_changed_source_header_aborts_instead_of_silently_dropping_data(self):
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'changed.zip'
   with zipfile.ZipFile(archive,'w') as z:
    z.writestr('olist_customers_dataset.csv','unexpected_column\nsome_value\n')
   with self.assertRaisesRegex(ValueError,'Invalid source header: customers'):
    prepare(archive,Path(tmp)/'clean')

 def test_money_rejects_nan_negative_and_extra_precision(self):
  for value in ('NaN','Infinity','-1','1.001','not-money'):
   with self.subTest(value=value), self.assertRaises(ValueError):
    money(value)
  self.assertEqual(money('10.5'),'10.50')

 def test_timestamps_are_validated_not_sliced(self):
  self.assertEqual(timestamp('',optional=True),'')
  for value in ('','2018-02-30 12:00:00','2018-13-01 00:00:00'):
   with self.subTest(value=value), self.assertRaises(ValueError):
    timestamp(value)

 def test_quarantine_preserves_valid_rows_and_review_grain(self):
  sources={
   'customers':[dict(customer_id=C,customer_state='SP'),dict(customer_id=C,customer_state='RJ')],
   'orders':[dict(order_id=A,customer_id=C,order_status='delivered',order_purchase_timestamp='2018-01-01 00:00:00',order_delivered_customer_date='',order_estimated_delivery_date='2018-01-03 00:00:00'),dict(order_id=B,customer_id='d'*32,order_status='delivered',order_purchase_timestamp='2018-01-01 00:00:00',order_delivered_customer_date='',order_estimated_delivery_date='2018-01-03 00:00:00')],
   'order_items':[dict(order_id=A,order_item_id='1',price='10.00',freight_value='2.50'),dict(order_id=A,order_item_id='1',price='20.00',freight_value='3.00'),dict(order_id=B,order_item_id='1',price='10',freight_value='2')],
   'order_reviews':[dict(review_id=B,order_id=A,review_score='2'),dict(review_id=B,order_id=A,review_score='4'),dict(review_id=C,order_id=A,review_score='9')]
  }
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'fixture.zip'
   with zipfile.ZipFile(archive,'w') as z:
    for name,rows in sources.items():
     stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
     z.writestr('olist_'+name+'_dataset.csv',stream.getvalue())
   report=prepare(archive,Path(tmp)/'clean')
   self.assertEqual(report['tables']['customers']['duplicate_key_rows'],1)
   self.assertEqual(report['tables']['orders']['rejection_reasons'],{'orphan_customer':1})
   self.assertEqual(report['tables']['order_items']['accepted_rows'],1)
   self.assertEqual(report['tables']['order_reviews']['accepted_rows'],2)
   self.assertEqual(report['tables']['order_reviews']['repeated_review_id_rows'],1)
   self.assertEqual(report['tables']['order_reviews']['rejection_reasons'],{'invalid_review_score':1})
   self.assertEqual(report['tables']['orders']['missing_by_source_column']['order_delivered_customer_date'],2)
   for counts in report['tables'].values():
    self.assertEqual(counts['source_rows'],counts['accepted_rows']+counts['rejected_rows'])

if __name__=='__main__':unittest.main()
