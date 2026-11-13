"""Audited PostgreSQL full-refresh pipeline using Python stdlib and psql."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from quality import prepare, TABLES
from download import EXPECTED

ROOT = Path(__file__).resolve().parent

def psql_binary():
 candidates = [os.environ.get('PSQL',''), shutil.which('psql'), '/opt/homebrew/opt/postgresql@18/bin/psql', '/opt/homebrew/opt/libpq/bin/psql']
 for candidate in candidates:
  if candidate and Path(candidate).is_file():
   return candidate
 raise RuntimeError('psql is required. Install PostgreSQL client tools; see README.')

def execute(dsn, sql):
 result = subprocess.run([psql_binary(), '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-d', dsn],
  input=sql, text=True, capture_output=True)
 if result.returncode:
  # Do not log the DSN/password.
  raise RuntimeError(result.stderr.strip())
 return result.stdout

def query(dsn, sql):
 return list(csv.DictReader(io.StringIO(execute(dsn, 'COPY ('+sql+') TO STDOUT WITH CSV HEADER;'))))

def write_csv(path, rows, fields=None):
 with path.open('w',newline='') as f:
  writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows)

def build(dsn, archive=None, reports=None):
 start = time.perf_counter(); archive=Path(archive or ROOT/'data/olist.zip'); out=Path(reports or ROOT/'reports');out.mkdir(parents=True,exist_ok=True)
 source_hash=hashlib.sha256(archive.read_bytes()).hexdigest()
 if source_hash != EXPECTED:
  raise ValueError('Archive checksum differs from the pinned Olist source. Review it before changing the pin.')
 with tempfile.TemporaryDirectory(prefix='delivery-clean-') as directory:
  staging=Path(directory); quality=prepare(archive,staging); validated=time.perf_counter()
  values = {}
  for table in ('order_items',):
   with (staging/(table+'.csv')).open() as f:
    rows=list(csv.DictReader(f))
   values['item_value']=sum((Decimal(r['price']) for r in rows),Decimal(0))
   values['freight_value']=sum((Decimal(r['freight_value']) for r in rows),Decimal(0))
  sql = 'BEGIN; SELECT pg_advisory_xact_lock(73218027);\n'+(ROOT/'sql/postgres/schema.sql').read_text()+'\n'
  sql += 'TRUNCATE delivery_insights.order_reviews, delivery_insights.order_items, delivery_insights.orders, delivery_insights.customers;\n'
  for table in TABLES:
   path=str(staging/(table+'.csv')).replace("'","''")
   sql += "\\copy delivery_insights."+table+" FROM '"+path+"' WITH (FORMAT csv, HEADER true)\n"
  expected_orders=quality['tables']['orders']['accepted_rows']
  sql += f"""
DO $$ BEGIN
 IF (SELECT COUNT(*) FROM delivery_insights.order_facts) <> {expected_orders} THEN RAISE EXCEPTION 'Order grain reconciliation failed'; END IF;
 IF (SELECT COALESCE(SUM(item_value),0) FROM delivery_insights.order_facts) <> {values['item_value']} THEN RAISE EXCEPTION 'Item value reconciliation failed'; END IF;
 IF (SELECT COALESCE(SUM(freight_value),0) FROM delivery_insights.order_facts) <> {values['freight_value']} THEN RAISE EXCEPTION 'Freight reconciliation failed'; END IF;
END $$;
COMMIT;
"""
  execute(dsn,sql); loaded=time.perf_counter()
 # Explicit sorting gives stable exports for replay comparison.
 exports = {
  'regions': 'SELECT * FROM delivery_insights.regional_metrics ORDER BY priority_rank,state',
  'trends': 'SELECT * FROM delivery_insights.monthly_metrics ORDER BY month',
  'reviews': "SELECT CASE WHEN late=1 THEN 'Late' ELSE 'On time' END delivery_outcome,COUNT(*) orders,COUNT(review_score) reviewed_orders,ROUND(AVG(review_score),6) average_review_score FROM delivery_insights.eligible GROUP BY late ORDER BY late",
 }
 results={name:query(dsn,statement) for name,statement in exports.items()}
 for name,rows in results.items():
  write_csv(out/(name+'.csv'),rows)
 summary=query(dsn,"SELECT COUNT(*) observed_deliveries,SUM(late) late_deliveries,ROUND(AVG(late)*100,6) late_pct,MIN(purchased_at)::date first_purchase,MAX(purchased_at)::date last_purchase FROM delivery_insights.eligible")[0]
 summary={k:(int(v) if k in ('observed_deliveries','late_deliveries') else float(v) if k=='late_pct' else v) for k,v in summary.items()}
 summary['excluded_orders']=expected_orders-summary['observed_deliveries']
 diagnostics=query(dsn,"SELECT COUNT(*) FILTER(WHERE delivered_at IS NULL) missing_delivery_timestamp,COUNT(*) FILTER(WHERE order_status='delivered' AND delivered_at IS NULL) delivered_without_timestamp,COUNT(*) FILTER(WHERE delivered_at < purchased_at) delivery_before_purchase,COUNT(*) FILTER(WHERE item_count=0) orders_without_items,COUNT(*) FILTER(WHERE review_score IS NULL) orders_without_reviews FROM delivery_insights.order_facts")[0]
 fingerprint=query(dsn,"SELECT MD5(STRING_AGG(ROW(order_id,state,month,order_status,item_value,freight_value,item_count,review_score,delay_days)::text,E'\\n' ORDER BY order_id)) fact_fingerprint FROM delivery_insights.order_facts")[0]['fact_fingerprint']
 quality.update(diagnostics={k:int(v) for k,v in diagnostics.items()}, reconciliation={
  'order_grain':{'passed':True,'expected':expected_orders,'actual':expected_orders},
  'item_value_brl':{'passed':True,'source_total':str(values['item_value']),'fact_total':str(values['item_value'])},
  'freight_value_brl':{'passed':True,'source_total':str(values['freight_value']),'fact_total':str(values['freight_value'])}})
 write_csv(out/'rejected_records.csv',quality['rejected_records'],['table','source_row','reason'])
 (out/'data_quality.json').write_text(json.dumps(quality,indent=2)+'\n')
 metrics=[]
 for r in results['regions']:
  metrics.append(dict(question='Regional priorities',state=r['state'],month='',delivery_outcome='',orders=r['orders'],late_orders=r['late_orders'],late_pct=r['late_pct'],average_review_score=r['average_review_score'],reviewed_orders='',change_percentage_points='',priority_rank=r['priority_rank']))
 for r in results['trends']:
  metrics.append(dict(question='Monthly reliability',state='',month=r['month'],delivery_outcome='',orders=r['orders'],late_orders=r['late_orders'],late_pct=r['late_pct'],average_review_score='',reviewed_orders='',change_percentage_points=r['change_percentage_points'],priority_rank=''))
 for r in results['reviews']:
  metrics.append(dict(question='Review association',state='',month='',delivery_outcome=r['delivery_outcome'],orders=r['orders'],late_orders='',late_pct='',average_review_score=r['average_review_score'],reviewed_orders=r['reviewed_orders'],change_percentage_points='',priority_rank=''))
 write_csv(out/'tableau_metrics.csv',metrics)
 hashes={name:hashlib.sha256((out/(name+'.csv')).read_bytes()).hexdigest() for name in (*exports,'tableau_metrics')}
 manifest={'generated_at':datetime.now(timezone.utc).isoformat(),'backend':'PostgreSQL','server_version':query(dsn,'SELECT version() server_version')[0]['server_version'],
  'archive_sha256':source_hash,'source_rows':{k:v['source_rows'] for k,v in quality['tables'].items()},'summary':summary,
  'fact_fingerprint':fingerprint,'export_sha256':hashes,'timing_seconds':{'validation':round(validated-start,3),'load_and_reconcile':round(loaded-validated,3),'total':round(time.perf_counter()-start,3)},
  'environment':{'platform':platform.system(),'machine':platform.machine(),'python':platform.python_version()},
  'source':'https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce'}
 (out/'warehouse_run.json').write_text(json.dumps(manifest,indent=2)+'\n')
 write_quality_report(out,quality,manifest)
 return manifest

def write_quality_report(out,q,manifest):
 lines=['# Data-quality report','', 'Generated from the pinned archive during the PostgreSQL build. Quarantine counts are observed, not planted demo defects.','',
  '| Source | Read | Accepted | Quarantined | Duplicate keys | Exact duplicates |','|---|---:|---:|---:|---:|---:|']
 for name,r in q['tables'].items():
  lines.append(f"| {name} | {r['source_rows']:,} | {r['accepted_rows']:,} | {r['rejected_rows']:,} | {r['duplicate_key_rows']:,} | {r['exact_duplicate_rows']:,} |")
 lines += ['', '## Missing source values', '', 'These counts cover every original source column, including columns not loaded into the warehouse. Optional empty fields are not automatically errors.','']
 for table,r in q['tables'].items():
  lines += [f'### {table}', '']+[f'- {column}: {count:,}' for column,count in r['missing_by_source_column'].items()]+['']
 lines += [f"Repeated review-ID rows: {q['tables']['order_reviews']['repeated_review_id_rows']:,}. Review IDs are not unique in this source; these rows are preserved, not mislabeled as duplicate primary keys.", '']
 lines += ['## Fact diagnostics','']+[f'- {key}: {value:,}' for key,value in q['diagnostics'].items()]
 lines += ['', '## Reconciliation', '', f"- One-row-per-order check: PASS ({manifest['summary']['observed_deliveries']+manifest['summary']['excluded_orders']:,} facts).",
  '- Item and freight totals: exact NUMERIC equality, checked inside the load transaction before commit.',
  '- Parent/child references and primary keys: enforced by PostgreSQL constraints.',
  '- Orders without delivery timestamps remain in facts, but are excluded from delivery-rate denominators.',
  '- Multiple review rows are averaged per order before computing group means. Review ID alone is not treated as unique.',
  '- Missing optional source fields, including review text, do not cause record rejection.', '', '## Quarantine policy', '', q['policy'],
  'Rejected source row numbers and reasons are in rejected_records.csv; review comments and personal free text are never exported.',
  'File-level header/CSV failures abort the build. A failed database transaction rolls back the refresh.',
  '', '## Scope', '', 'Only the four required tables are validated. This is not an audit of every Olist dataset. First-valid-row duplicate handling is deterministic, but a production system would require business approval before resolving conflicting duplicates.',
  'The source contains historical marketplace data, not current PEI operating data. No patient data are used.']
 (out/'data_quality.md').write_text('\n'.join(lines)+'\n')

def benchmark(dsn,runs=3):
 if runs<2:
  raise ValueError('At least two runs are required to measure repeatability.')
 manifests=[build(dsn) for _ in range(runs)]
 stable=all((m['summary'],m['fact_fingerprint'],m['export_sha256'])==(manifests[0]['summary'],manifests[0]['fact_fingerprint'],manifests[0]['export_sha256']) for m in manifests)
 result={'runs':runs,'identical_metrics_facts_and_exports':stable,'load_strategy':'Transactional full refresh, not append; warm local runs, no network download included.',
  'measurements':[{'run':i+1,'timing_seconds':m['timing_seconds'],'observed_deliveries':m['summary']['observed_deliveries'],'late_deliveries':m['summary']['late_deliveries'],'fact_fingerprint':m['fact_fingerprint']} for i,m in enumerate(manifests)],
  'environment':manifests[-1]['environment'],'server_version':manifests[-1]['server_version']}
 (ROOT/'reports/benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
 if not stable:
  raise AssertionError('Repeated imports changed facts, metrics, or exports.')
 return result

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database-url',default=os.environ.get('DATABASE_URL'));parser.add_argument('--benchmark',type=int,default=0)
 args=parser.parse_args()
 if not args.database_url:
  parser.error('Set DATABASE_URL or pass --database-url. Use a dedicated development database.')
 print(json.dumps(benchmark(args.database_url,args.benchmark) if args.benchmark else build(args.database_url),indent=2))
