"""Validate source records before PostgreSQL COPY. No external dependencies."""
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
import csv
import io
import re
import zipfile

TABLES = ('customers', 'orders', 'order_items', 'order_reviews')
FIELDS = {
 'customers': ('customer_id', 'customer_state'),
 'orders': ('order_id','customer_id','order_status','purchased_at','delivered_at','estimated_at'),
 'order_items': ('order_id','order_item_id','price','freight_value'),
 'order_reviews': ('source_row','review_id','order_id','review_score'),
}
STATES = set('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())
STATUSES = set('created approved invoiced processing shipped delivered unavailable canceled'.split())
REQUIRED_SOURCE = {
 'customers': {'customer_id','customer_state'},
 'orders': {'order_id','customer_id','order_status','order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date'},
 'order_items': {'order_id','order_item_id','price','freight_value'},
 'order_reviews': {'review_id','order_id','review_score'},
}

def identifier(value):
 if not re.fullmatch(r'[0-9a-f]{32}', value or ''):
  raise ValueError('invalid_identifier')
 return value

def timestamp(value, optional=False):
 if not value and optional:
  return ''
 try:
  return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').isoformat(' ')
 except (ValueError, TypeError):
  raise ValueError('invalid_or_missing_timestamp') from None

def money(value):
 try:
  n = Decimal(value)
  if not n.is_finite() or n < 0 or n != n.quantize(Decimal('.01')) or n >= Decimal('1000000000000'):
   raise ValueError('invalid_money')
  return str(n.quantize(Decimal('.01')))
 except (InvalidOperation, TypeError):
  raise ValueError('invalid_money') from None

def validate_record(table, row, row_number, known):
 if table == 'customers':
  cid = identifier(row.get('customer_id'))
  if row.get('customer_state') not in STATES:
   raise ValueError('invalid_state')
  return (cid,), {'customer_id':cid, 'customer_state':row['customer_state']}
 oid = identifier(row.get('order_id'))
 if table == 'orders':
  cid = identifier(row.get('customer_id'))
  if cid not in known['customers']:
   raise ValueError('orphan_customer')
  if row.get('order_status') not in STATUSES:
   raise ValueError('invalid_status')
  result = dict(order_id=oid, customer_id=cid, order_status=row['order_status'],
   purchased_at=timestamp(row.get('order_purchase_timestamp')),
   delivered_at=timestamp(row.get('order_delivered_customer_date'), optional=True),
   estimated_at=timestamp(row.get('order_estimated_delivery_date')))
  return (oid,), result
 if oid not in known['orders']:
  raise ValueError('orphan_order')
 if table == 'order_items':
  try:
   item = int(row.get('order_item_id',''))
   if item <= 0:
    raise ValueError()
  except (ValueError, TypeError):
   raise ValueError('invalid_item_number') from None
  return (oid,item), dict(order_id=oid, order_item_id=item, price=money(row.get('price')), freight_value=money(row.get('freight_value')))
 rid = identifier(row.get('review_id'))
 try:
  score = int(row.get('review_score',''))
  if score not in range(1,6):
   raise ValueError()
 except (ValueError, TypeError):
  raise ValueError('invalid_review_score') from None
 # A review ID alone is not a unique key in this source. Preserve legitimate repeated reviews.
 return (row_number,), dict(source_row=row_number, review_id=rid, order_id=oid, review_score=score)

def prepare(archive, output_dir):
 output_dir.mkdir(parents=True, exist_ok=True)
 report = {'tables':{}, 'rejected_records':[], 'policy':'First valid primary-key row wins; subsequent duplicate keys quarantined. Reviews preserve source-row grain. Empty optional delivered timestamps remain null.'}
 known = {'customers':set(), 'orders':set()}
 with zipfile.ZipFile(archive) as z:
  for table in TABLES:
   accepted, seen, missing, reasons = [], set(), Counter(), Counter()
   raw_seen, exact_duplicates, review_ids = set(), 0, Counter()
   count = 0
   with z.open('olist_'+table+'_dataset.csv') as source:
    reader=csv.DictReader(io.TextIOWrapper(source, encoding='utf-8-sig'))
    if not reader.fieldnames or not REQUIRED_SOURCE[table].issubset(reader.fieldnames) or len(reader.fieldnames)!=len(set(reader.fieldnames)):
     raise ValueError('Invalid source header: '+table)
    for count,row in enumerate(reader, start=1):
     if None in row or any(v is None for v in row.values()):
      raise ValueError('Malformed CSV row: '+table+' row '+str(count))
     raw_key=tuple(row.items())
     exact_duplicates += raw_key in raw_seen
     raw_seen.add(raw_key)
     if table=='order_reviews':review_ids[row['review_id']] += 1
     missing.update(k for k,v in row.items() if v is None or v.strip() == '')
     try:
      key, clean = validate_record(table,row,count,known)
      if key in seen:
       raise ValueError('duplicate_primary_key')
      seen.add(key); accepted.append(clean)
      if table in known:
       known[table].add(key[0])
     except ValueError as error:
      reason = str(error); reasons[reason] += 1
      report['rejected_records'].append(dict(table=table, source_row=count, reason=reason))
   with (output_dir/(table+'.csv')).open('w', newline='') as f:
    writer=csv.DictWriter(f,fieldnames=FIELDS[table]);writer.writeheader();writer.writerows(accepted)
   report['tables'][table] = dict(source_rows=count, accepted_rows=len(accepted), rejected_rows=sum(reasons.values()), exact_duplicate_rows=exact_duplicates,
     duplicate_key_rows=reasons['duplicate_primary_key'], rejection_reasons=dict(reasons), missing_by_source_column=dict(sorted(missing.items())))
   if table=='order_reviews':report['tables'][table]['repeated_review_id_rows']=sum(n-1 for n in review_ids.values())
 return report
