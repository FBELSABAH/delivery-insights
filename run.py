"""Build a reproducible SQLite warehouse, exports and offline dashboard. Python standard library only."""
from pathlib import Path
import csv, sqlite3, zipfile, hashlib, json, html, time
ROOT=Path(__file__).resolve().parent

def findings_markdown(results):
    summary = results["summary"]
    largest = results["regions"][0]
    source_orders = results["provenance"]["source_rows"]["orders"]
    review_rows = [
        "| Delivery outcome | Orders with a review | Mean review score (out of 5) |",
        "| --- | ---: | ---: |",
    ]
    for group in sorted(results["reviews"], key=lambda row: row["late"]):
        label = "Late" if group["late"] else "On time or early"
        mean = group["average_score"]
        score = f"{mean:.2f}" if mean is not None else "—"
        review_rows.append(f"| {label} | {group['reviewed_orders']:,} | {score} |")
    review_table = "\n".join(review_rows)

    return f"""# Delivery investigation brief

Of {source_orders:,} Olist orders, {summary['observed_deliveries']:,} were delivered with usable dates. **{summary['late_deliveries']:,} ({summary['late_pct']:.2f}%) arrived late.** The rate excludes {summary['excluded_orders']:,} orders. A delivery is late when it arrives after the promised calendar date.

## Where to investigate

Customer state **{largest['state']}** had the most late deliveries ({largest['late_orders']:,}). The regional table reports both the count and the rate for states with at least 100 eligible orders. High order volume can produce many late deliveries even when the rate is relatively low. [Compare states](regions.csv) or [see the monthly trend](trends.csv).

## What customers reported

{review_table}

Each reviewed order counts once. Multiple reviews for an order are averaged first. Orders without a review are excluded from the score averages, and customers who leave reviews may differ from those who do not. These historical observations cannot identify a carrier or explain what caused a rating.

[Metric definitions](../../sql/model.sql) · [Source, row counts, and build results](results.json)
"""


def build():
 start=time.perf_counter(); out=ROOT/'reports/legacy';out.mkdir(parents=True,exist_ok=True)
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
 (out/'findings.md').write_text(findings_markdown(results), encoding='utf-8')
 payload=json.dumps(results).replace('<','\u003c')
 template=(ROOT/'dashboard.html').read_text();(out/'dashboard.html').write_text(template.replace('/*DATA*/{}',payload))
 print(json.dumps(results['summary'],indent=2));print('Build and reconciliation checks passed.')
if __name__=='__main__':build()
