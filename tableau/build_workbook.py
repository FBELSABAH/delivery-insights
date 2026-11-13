"""Build a portable native workbook from a Tableau-created data-source template.
Run after exporting fresh metrics. Pass a saved Tableau TWB containing its Hyper extract.
"""
from pathlib import Path
import argparse, copy, csv, json, shutil, uuid, zipfile
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]

def sub(parent,tag,**attrs):return E.SubElement(parent,tag,{k.replace('_','-'):str(v) for k,v in attrs.items()})
def build(template):
 tree=E.parse(template);root=tree.getroot()
 for key in list(root.attrib):
  if 'Fingerprint' in key or 'author' in key or 'machine' in key: del root.attrib[key]
 for child in list(root):
  if child.tag in ('worksheets','windows','thumbnails','dashboards'):root.remove(child)
 ds=root.find('datasources/datasource');dsn=ds.attrib['name'];ds.set('caption','Olist | validated operational metrics')
 ex=ds.find('extract/connection');hyper=Path(ex.attrib['dbname'])
 data=ROOT/'tableau/Data';data.mkdir(exist_ok=True)
 shutil.copy2(hyper,data/'Delivery_Insights.hyper');shutil.copy2(ROOT/'reports/tableau_metrics.csv',data/'tableau_metrics.csv')
 ex.set('dbname','Data/Delivery_Insights.hyper');ex.attrib.pop('update-time',None)
 for conn in ds.findall('.//named-connection/connection'):
  if conn.get('class')=='textscan':conn.set('directory','Data')
 for c in ds.findall('column'):
  if c.get('name')=='[state]':c.attrib.pop('semantic-role',None)
 for elem in ds.findall('semantic-values'):ds.remove(elem)
 # Discrete string permits a chronological monthly axis without accidental year-only grouping.
 rankcol=sub(ds,'column',caption='Priority / state',datatype='string',name='[ranked_state]',role='dimension',type='ordinal')
 sub(rankcol,'calculation',**{'class':'tableau','formula':'RIGHT("0" + STR(INT([priority_rank])),2) + "  " + [state]'})
 calc=sub(ds,'column',caption='Purchase month',datatype='string',name='[month_label]',role='dimension',type='ordinal')
 sub(calc,'calculation',**{'class':'tableau','formula':'RIGHT(STR(YEAR([month])),2) + "-" + RIGHT("0" + STR(MONTH([month])), 2)'})
 inc=sub(ds,'column',caption='Include reliable month',datatype='boolean',name='[include_month]',role='dimension',type='nominal')
 sub(inc,'calculation',**{'class':'tableau','formula':'[question] = "Monthly reliability" AND [orders] >= 100'})
 # Tableau requires columns before extract/layout/object-graph in its XML content model.
 for field in (rankcol, calc, inc):
  ds.remove(field);ds.insert(list(ds).index(ds.find('extract')),field)
 columns={c.attrib['name']:c for c in ds.findall('column')}
 for name in ('[late_pct]','[average_review_score]'):columns[name].set('default-format','n0.0' if name=='[late_pct]' else 'n0.00')
 sheets=sub(root,'worksheets')
 specs=[('1a | Top 10 investigation regions','Regional priorities','ranked_state','late_orders','Sum','Bar','#0f766e'),('1b | Late rate in those regions (%)','Regional priorities','ranked_state','late_pct','Avg','Bar','#b45309'),('2 | Monthly late rate (%) - n >= 100','Monthly reliability','month_label','late_pct','Avg','Line','#0f766e'),('3 | Review scores by outcome (1-5)','Review association','delivery_outcome','average_review_score','Avg','Bar','#334155')]
 def full(field):return '['+dsn+'].'+field
 for title,question,dim,measure,agg,mark,color in specs:
  sheet=sub(sheets,'worksheet',name=title);layout=sub(sheet,'layout-options');tt=sub(layout,'title');ft=sub(tt,'formatted-text');sub(ft,'run',fontname='Arial',fontsize='10',bold='true').text=title
  table=sub(sheet,'table');view=sub(table,'view');sources=sub(view,'datasources');sub(sources,'datasource',caption=ds.get('caption'),name=dsn)
  deps=sub(view,'datasource-dependencies',datasource=dsn)
  used=[dim,measure,'priority_rank','state','question','orders','reviewed_orders','late_orders','late_pct','average_review_score']
  if question=='Monthly reliability':used+=['include_month','month']
  instances={}
  for field in dict.fromkeys(used):
   col=copy.deepcopy(columns['['+field+']']);deps.append(col)
   dimension=col.get('role')=='dimension';derivation='None' if dimension else agg if field==measure else 'Sum' if field in ('orders','late_orders','reviewed_orders') else 'Avg'
   suffix='ok' if col.get('type')=='ordinal' else 'nk' if dimension else 'qk';prefix='none' if dimension else derivation.lower()
   instance=f'[{prefix}:{field}:{suffix}]';instances[field]=instance
   sub(deps,'column-instance',column='['+field+']',derivation=derivation,name=instance,pivot='key',type=col.get('type'))
  filt=sub(view,'filter',**{'class':'categorical','column':full(instances['question'])});sub(filt,'groupfilter',function='member',level=instances['question'],member='"'+question+'"')
  if question=='Monthly reliability':
   filt=sub(view,'filter',**{'class':'categorical','column':full(instances['include_month'])});sub(filt,'groupfilter',function='member',level=instances['include_month'],member='true')
  if question=='Regional priorities':
   top=sub(view,'filter',**{'class':'categorical','column':full(instances['ranked_state'])});union=sub(top,'groupfilter',function='union',level=instances['ranked_state'])
   with (ROOT/'reports/regions.csv').open() as rf:
    for r in list(csv.DictReader(rf))[:10]:sub(union,'groupfilter',function='member',level=instances['ranked_state'],member='"'+str(r['priority_rank']).zfill(2)+'  '+r['state']+'"')
  sub(view,'aggregation',value='true')
  style=sub(table,'style');rule=sub(style,'style-rule',element='mark');sub(rule,'format',attr='mark-color',value=color);sub(rule,'format',attr='mark-labels-show',value='true' if mark=='Bar' else 'false')
  rule=sub(style,'style-rule',element='cell');sub(rule,'format',attr='font-family',value='Arial');sub(rule,'format',attr='font-size',value='10')
  rule=sub(style,'style-rule',element='axis');sub(rule,'format',attr='font-size',value='9')
  panes=sub(table,'panes');pane=sub(panes,'pane',selection_relaxation_option='selection-relaxation-allow');pv=sub(pane,'view');sub(pv,'breakdown',value='auto');sub(pane,'mark',**{'class':mark})
  enc=sub(pane,'encodings');sub(enc,'tooltip',column=full(instances['orders']))
  if mark=='Bar':sub(enc,'text',column=full(instances[measure]))
  tip=sub(pane,'customized-tooltip');formatted=sub(tip,'formatted-text')
  sub(formatted,'run').text=f'<{full(instances[dim])}>\n{measure}: <{full(instances[measure])}>\nEligible orders: <{full(instances["orders"])}>'
  if question=='Review association':sub(enc,'tooltip',column=full(instances['reviewed_orders']));sub(formatted,'run').text=f'\nReviewed orders: <{full(instances["reviewed_orders"])}>\nDescriptive association; not a causal effect.'
  sub(table,'rows').text=full(instances[measure]) if mark=='Line' else full(instances[dim])
  sub(table,'cols').text=full(instances[dim]) if mark=='Line' else full(instances[measure])
  sub(sheet,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')
 dashboards=sub(root,'dashboards');dash=sub(dashboards,'dashboard',name='Delivery Insights | Operations review');style=sub(dash,'style');rule=sub(style,'style-rule',element='dashboard');sub(rule,'format',attr='background-color',value='#f1f5f9')
 sub(dash,'size',maxheight='660',maxwidth='1000',minheight='660',minwidth='1000')
 zones=sub(dash,'zones');base=sub(zones,'zone',h='100000',id='1',type_v2='layout-basic',w='100000',x='0',y='0')
 run=json.loads((ROOT/'reports/warehouse_run.json').read_text());s=run['summary']
 def textzone(id,x,y,w,h,text,size,color='#0f172a'):
  z=sub(base,'zone',id=id,x=x,y=y,w=w,h=h,type_v2='text');ft=sub(z,'formatted-text');sub(ft,'run',fontname='Arial',fontsize=size,fontcolor=color).text=text;zs=sub(z,'zone-style');sub(zs,'format',attr='margin',value='12');return z
 textzone(2,1000,500,98000,10000,f'DELIVERY INSIGHTS  /  OPERATIONS REVIEW\n{s["observed_deliveries"]:,} eligible deliveries   |   {s["late_deliveries"]:,} late   |   {s["late_pct"]:.2f}% late\n',10)
 for i,(title,*_) in enumerate(specs):
  x,y,w,h=[(1500,11500,48000,38500),(51000,11500,47500,38500),(1500,52500,60000,30000),(63500,52500,35000,30000)][i]
  z=sub(base,'zone',id=i+3,name=title,x=x,y=y,w=w,h=h);zs=sub(z,'zone-style');sub(zs,'format',attr='background-color',value='#ffffff');sub(zs,'format',attr='margin',value='10')
 textzone(8,1500,85000,97000,14000,'READ BEFORE ACTING\nRegion = customer state; it does not identify a responsible carrier. Regional charts require n >= 100. Monthly trend excludes n < 100; latest cohorts have incomplete follow-up. Review means exclude missing scores and average repeated reviews within each order.\nSource: Olist and collaborators / Kaggle Brazilian E-Commerce Public Dataset. CC BY-NC-SA 4.0. No observed delivery improvement or financial savings.',8,'#475569')
 sub(base,'zone-style');sub(dash,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')
 windows=sub(root,'windows')
 for title,*_ in specs:
  sw=sub(windows,'window',**{'class':'worksheet','name':title,'maximized':'true'});sub(sw,'cards');sub(sw,'viewpoint');sub(sw,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')
 window=sub(windows,'window',**{'class':'dashboard','name':dash.get('name'),'maximized':'true'});vps=sub(window,'viewpoints')
 for title,*_ in specs:
  vp=sub(vps,'viewpoint',name=title);sub(vp,'zoom',type='entire-view')
 sub(window,'active',id='-1');sub(window,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')
 E.indent(tree,space='  ');target=ROOT/'tableau/Delivery_Insights.twb';tree.write(target,encoding='utf-8',xml_declaration=True)
 with zipfile.ZipFile(ROOT/'tableau/Delivery_Insights.twbx','w',zipfile.ZIP_DEFLATED) as z:
  for p in (target,data/'Delivery_Insights.hyper',data/'tableau_metrics.csv'):z.write(p,str(p.relative_to(ROOT/'tableau')))
 print('Built native Tableau workbook with four sheets and an operations dashboard.')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('template',type=Path);build(parser.parse_args().template)
