"""Build a reproducible SQLite warehouse, exports and offline dashboard. Python standard library only."""
from pathlib import Path
import csv, sqlite3, zipfile, hashlib, json, html, time
ROOT=Path(__file__).resolve().parent

def build():
 start=time.perf_counter(); out=ROOT/'reports';out.mkdir(exist_ok=True)
 archive=ROOT/'data/olist.zip'
 if not archive.exists(): raise SystemExit('Download Olist to data/olist.zip; see README.md')
 db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
 counts={}
 with zipfile.ZipFile(archive) as z:
  for name in ['orders','customers','order_items','order_reviews']:
   import io
   rows=csv.reader(io.TextIOWrapper(z.open('olist_'+name+'_dataset.csv'),encoding='utf-8-sig'))
   header=next(rows);db.execute('CREATE TABLE '+name+' ('+','.join('"'+x+'" TEXT' for x in header)+')')
   db.executemany('INSERT INTO '+name+' VALUES ('+','.join('?' for _ in header)+')',rows)
   counts[name]=db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
 for table,key in [('orders','order_id'),('customers','customer_id')]:
  n=db.execute(f'SELECT COUNT(*)-COUNT(DISTINCT {key}) FROM {table}').fetchone()[0]
  if n: raise ValueError('Duplicate primary keys: '+table)
 for table,key in [('orders','order_id'),('customers','customer_id'),('order_items','order_id'),('order_reviews','order_id')]:db.execute(f'CREATE INDEX idx_{table} ON {table}({key})')
 db.executescript((ROOT/'sql/model.sql').read_text())
 assert db.execute('SELECT COUNT(*) FROM order_facts').fetchone()[0]==counts['orders'], 'Join multiplied orders'
 expected=db.execute('SELECT SUM(CAST(price AS REAL)) FROM order_items').fetchone()[0]
 actual=db.execute('SELECT SUM(item_value) FROM order_facts').fetchone()[0]
 assert abs(expected-actual)<.01,'Item value reconciliation failed'
 results={}
 for label,file in [('regions','analysis.sql'),('trends','trends.sql')]:
  rows=[dict(r) for r in db.execute((ROOT/'sql'/file).read_text())];results[label]=rows
  with (out/(label+'.csv')).open('w') as f:
   w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 summary=dict(db.execute('SELECT COUNT(*) observed_deliveries,SUM(late) late_deliveries,AVG(late)*100 late_pct FROM eligible').fetchone())
 summary['excluded_orders']=counts['orders']-summary['observed_deliveries']
 results['reviews']=[dict(r) for r in db.execute('SELECT late,COUNT(review_score) reviewed_orders,AVG(review_score) average_score FROM eligible GROUP BY late')]
 results['summary']=summary
 results['provenance']={'source':'https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_rows':counts,'build_seconds':round(time.perf_counter()-start,3)}
 (out/'results.json').write_text(json.dumps(results,indent=2))
 target=sqlite3.connect(str(ROOT/'data/analytics.sqlite'));db.backup(target);target.close()
 top=results['regions'][0]
 (out/'findings.md').write_text(f"# Delivery investigation brief\n\nObserved {summary['observed_deliveries']:,} delivered orders with usable dates; {summary['late_deliveries']:,} were late ({summary['late_pct']:.2f}%). Excluded {summary['excluded_orders']:,} orders from this metric.\n\nFirst investigation region: {top['state']}, with {top['late_orders']:,} late deliveries. Prioritize by incident volume; the dashboard also shows rates to distinguish scale from reliability. Investigate carriers, routes and promises before changing operations.\n\nReviews by delivery outcome: {json.dumps(results['reviews'])}. This is descriptive association, not a causal effect. Missing reviews may be selective.\n\nMeasured technical impact: automated ingestion, four-table reconciliation, ranked geographic analysis and month-over-month reporting in {results['provenance']['build_seconds']} seconds on this run. No revenue uplift or delivery improvement has been observed.\n\nHistorical 2016–2018 marketplace sample; no claim of current operating performance. Late means delivered calendar date after promised calendar date. Multiple reviews are averaged per order; missing reviews are excluded from review means. Item value excludes freight and is not profit.\n")
 payload=json.dumps(results).replace('<','\u003c')
 template=(ROOT/'dashboard.html').read_text();(out/'dashboard.html').write_text(template.replace('/*DATA*/{}',payload))
 print(json.dumps(results['summary'],indent=2));print('Build and reconciliation checks passed.')
if __name__=='__main__':build()
