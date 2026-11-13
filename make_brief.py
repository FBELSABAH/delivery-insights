"""Render the one-page decision brief from verified warehouse outputs (ReportLab)."""
from pathlib import Path
import csv,json,statistics
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
ROOT=Path(__file__).resolve().parent

def render():
 out=ROOT/'reports';run=json.loads((out/'warehouse_run.json').read_text());q=json.loads((out/'data_quality.json').read_text());bench=json.loads((out/'benchmark.json').read_text())
 if not bench['identical_metrics_facts_and_exports']:
  raise ValueError('Cannot publish a brief for a failed replay benchmark')
 def rows(name):
  with (out/(name+'.csv')).open() as f:return list(csv.DictReader(f))
 regions=rows('regions');months=[r for r in rows('trends') if int(r['orders'])>=100];reviews={r['delivery_outcome']:r for r in rows('reviews')};s=run['summary']
 sp=next(r for r in regions if r['state']=='SP');rj=next(r for r in regions if r['state']=='RJ');peak=max(months,key=lambda r:float(r['late_pct']));late=reviews['Late'];ontime=reviews['On time']
 timings=[m['timing_seconds']['total'] for m in bench['measurements']];median=statistics.median(timings)
 styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='TitleDI',fontName='Helvetica-Bold',fontSize=25,leading=29,textColor=colors.HexColor('#123c43'),spaceAfter=5))
 styles.add(ParagraphStyle(name='DeckDI',fontName='Helvetica',fontSize=10,leading=14,textColor=colors.HexColor('#52616b'),spaceAfter=12))
 styles.add(ParagraphStyle(name='HeadDI',fontName='Helvetica-Bold',fontSize=11,leading=15,textColor=colors.HexColor('#0f766e'),spaceBefore=10,spaceAfter=4))
 styles.add(ParagraphStyle(name='BodyDI',fontName='Helvetica',fontSize=10.2,leading=14,spaceAfter=5,textColor=colors.HexColor('#243442')))
 styles.add(ParagraphStyle(name='FootDI',fontName='Helvetica',fontSize=8,leading=10,textColor=colors.HexColor('#52616b')))
 p=lambda text,style='BodyDI':Paragraph(text,styles[style])
 story=[p('Delivery Insights','TitleDI'),p('DECISION BRIEF  |  Historical marketplace delivery investigations','DeckDI')]
 kpis=[[p(f'<b>{s["observed_deliveries"]:,}</b><br/>eligible deliveries'),p(f'<b>{s["late_pct"]:.2f}%</b><br/>late-delivery rate'),p(f'<b>{median:.2f} seconds</b><br/>median full rebuild')]]
 t=Table(kpis,colWidths=[174,174,174]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf5f3')),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#d1e2de')),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story+=[t]
 def section(title,text):story.extend([p(title,'HeadDI'),p(text)])
 share=(int(sp['late_orders'])+int(rj['late_orders']))/s['late_deliveries']*100
 section('1 / Investigate scale and reliability separately',f'SP recorded {int(sp["late_orders"]):,} late deliveries at {float(sp["late_pct"]):.2f}%; RJ recorded {int(rj["late_orders"]):,} at {float(rj["late_pct"]):.2f}%. Together they account for {share:.1f}% of observed late deliveries. Start by comparing routes, sellers and delivery promises in these regions. Customer state alone cannot identify the responsible carrier or cause.')
 section('2 / Review the periods with elevated late rates',f'Among purchase months with at least 100 eligible deliveries, {peak["month"][:7]} had the highest late rate: {float(peak["late_pct"]):.2f}% across {int(peak["orders"]):,} orders. Compare its order mix, promises and operating conditions with adjacent months. Keep cohort follow-up consistent before judging later periods; the source ends in 2018.')
 section('3 / Examine the review association, then test explanations',f'Late deliveries averaged {float(late["average_review_score"]):.2f}/5 versus {float(ontime["average_review_score"]):.2f}/5 for on-time deliveries. Reviews cover {int(late["reviewed_orders"]):,}/{int(late["orders"]):,} late and {int(ontime["reviewed_orders"]):,}/{int(ontime["orders"]):,} on-time orders. These groups may differ in other ways; the score gap is not a causal effect or a forecast of improvement.')
 section('Data quality and measured technical results',f'The warehouse retained {q["tables"]["orders"]["accepted_rows"]:,} orders and excluded {s["excluded_orders"]:,} from delivery metrics. There were {q["diagnostics"]["missing_delivery_timestamp"]:,} missing actual delivery timestamps, including {q["diagnostics"]["delivered_without_timestamp"]} delivered-status orders. No records were quarantined under the declared rules. Order grain and BRL item/freight totals reconcile exactly. All {bench["runs"]} full refreshes produced identical facts, metrics and exports ({min(timings):.2f}-{max(timings):.2f}s; local warm runs, download excluded).')
 section('Scope and next decision','Late means delivered calendar date after promised date. Review rows are averaged within each order before group comparison. Regional charts require 100 eligible orders. Validate the proposed investigations with an operations owner before recommending changes. No actual delivery reduction, cost saving or customer adoption has been demonstrated.')
 story += [Spacer(1,9),p('Source: Olist and collaborators, Brazilian E-Commerce Public Dataset (2016-2018), Kaggle. CC BY-NC-SA 4.0. Portfolio analysis; not commissioned by Olist. Runtime: '+escape(bench['environment']['platform']+' '+bench['environment']['machine']+', Python '+bench['environment']['python']+'. PostgreSQL 18; exact version in benchmark.json.'),'FootDI')]
 doc=SimpleDocTemplate(str(out/'decision_brief.pdf'),pagesize=(612,792),rightMargin=45,leftMargin=45,topMargin=32,bottomMargin=30,title='Delivery Insights - Decision Brief',author='Faris Elsabah')
 prose=[x.text for x in story if isinstance(x,Paragraph)]
 doc.build(story)
 (out/'findings.md').write_text('# Delivery investigation brief\n\n'+ '\n\n'.join(x for x in prose)+'\n')
 print(out/'decision_brief.pdf')
if __name__=='__main__':render()
