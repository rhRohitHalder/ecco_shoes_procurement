#!/usr/bin/env python3
"""Reproducible synthetic ECCO-like procurement dataset; not company actuals."""
import csv, random, math, calendar, zipfile, os, json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date

R=random.Random(27102026)
OUT=Path('ECCO_Procurement_Synthetic_2020_2026')
OUT.mkdir(exist_ok=True)
counts={}
def write(name, rows, fields):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    counts[name]=len(rows)
def rowsave(name, rows):
    write(name,rows,list(rows[0]))
def n(x): return round(x,4)

months=[f'{y}-{m:02d}-01' for y in range(2020,2027) for m in range(1,13) if (y,m)<=(2026,9)]
plants=[('1001','Production Portugal','PT','EUR'),('1002','Production Slovakia','SK','EUR'),('1003','Production Thailand','TH','THB'),('1004','Production Indonesia','ID','IDR'),('1005','Production Vietnam','VN','VND'),('1006','Production China','CN','CNY')]
write('dim_plant.csv',[dict(plant_id=a,plant_name=b,country_code=c,local_currency=d,purch_org_id='1001' if i<2 else '2001') for i,(a,b,c,d) in enumerate(plants)],['plant_id','plant_name','country_code','local_currency','purch_org_id'])
org=[dict(purch_org_id='1001',purch_org_name='PTG Purchasing'),dict(purch_org_id='2001',purch_org_name='APAC Purchasing')]
rowsave('dim_purchasing_org.csv',org)

families=[('Lining','050122','PAA','Cotton'),('Leather upper','050110','SQM','Crude Oil'),('Outsole','050210','PAA','Rubber'),('Midsole','050220','PAA','Polyester'),('Insole','050230','PAA','Polyamide'),('Thread','050310','KG','Cotton'),('Adhesive','050320','KG','Benzene'),('Eyelets','050330','PAA','Copper + Zinc'),('Packaging paper','050410','KG','Paper'),('Shoe lace','050420','PAA','Polyester'),('Foam','050430','KG','Adipic Acid'),('Coating','050440','KG','Methanol')]
commodities=['Coal','Adipic Acid','Benzene','Cotton','Copper + Zinc','Crude Oil','Methanol','Natural Gas','Paper','Polyamide','Polyester','Rubber','Wool']
commodity_ids={x:f'CMD{i+1:02d}' for i,x in enumerate(commodities)}
unit={'Coal':'USD/metric_ton','Adipic Acid':'USD/metric_ton','Benzene':'USD/metric_ton','Cotton':'USD/kg','Copper + Zinc':'USD/metric_ton','Crude Oil':'USD/barrel','Methanol':'USD/metric_ton','Natural Gas':'USD/MMBtu','Paper':'USD/metric_ton','Polyamide':'USD/metric_ton','Polyester':'USD/metric_ton','Rubber':'USD/kg','Wool':'USD/kg'}
base={'Coal':90,'Adipic Acid':1400,'Benzene':800,'Cotton':1.8,'Copper + Zinc':7400,'Crude Oil':64,'Methanol':320,'Natural Gas':3.3,'Paper':780,'Polyamide':2600,'Polyester':1250,'Rubber':1.65,'Wool':12.5}
rowsave('dim_commodity',[dict(commodity_id=commodity_ids[c],commodity_name=c,index_unit=unit[c],source_label='SYNTHETIC blended market benchmark',source_type='simulated') for c in commodities])

vendor_countries=['PT','SK','IT','ES','TR','IN','CN','VN','TH','ID','DE','BR']
vendor_prefix=['Atlas','Meridian','Nova','Evergreen','Summit','Aster','Pacific','Prime','Sterling','Lotus','Orion','Crest','Delta','Sierra','Global','Sunrise','Vertex','Crown','Silver','Boreal']
vendor_suffix=['Footwear Components','Materials','Textiles','Polymers','Industrial Supply','Trading','Leatherworks','Rubber Co','Accessories']
vendors=[]
for i in range(95):
    vid=str(100021+i)
    name='Althaf Shoes PVT. Ltd.' if i==0 else f'{vendor_prefix[i%len(vendor_prefix)]} {vendor_suffix[(i//len(vendor_prefix)+i)%len(vendor_suffix)]} {i+1:03d}'
    country=vendor_countries[i%len(vendor_countries)]
    currency={'PT':'EUR','SK':'EUR','IT':'EUR','ES':'EUR','TR':'TRY','IN':'INR','CN':'CNY','VN':'VND','TH':'THB','ID':'IDR','DE':'EUR','BR':'BRL'}[country]
    vendors.append(dict(vendor_id=vid,vendor_name=name,vendor_country=country,preferred_currency=currency,approved_status='Approved' if i%13 else 'Conditional',payment_terms_days=[30,45,60,90][i%4],incoterm=['FOB','EXW','DAP','CIF'][i%4],vendor_tier=['Strategic','Preferred','Approved'][i%3]))
rowsave('dim_vendor.csv',vendors)

materials=[]; bridges=[]; mappings=[]
for i in range(1200):
    fam,group,uom,main=families[i%len(families)]
    mat7=f'C{220000+(i//6):06d}'
    mat=f'{mat7}{i%6+1:05d}'
    style=['Classic','Performance','Urban','Kids','Outdoor'][i%5]
    desc=('Pure sock - Vitrus Mondial' if i==0 else f'{fam} - {style} {i//12+1:03d}')
    materials.append(dict(material_id=mat,material_7=mat7,material_description=desc,material_group_id=group,material_group_name=fam,base_uom=uom,product_category=['Casual','Sport','Formal','Outdoor'][i%4],active_from=months[(i%8)],active_to='' if i%19 else '2025-12-31'))
    # 2–4 vendor possibilities, with one vendor often not actually ordered in a given year.
    num=2+(i%3==0)+(i%11==0)
    selected=R.sample(vendors,num)
    for j,v in enumerate(selected):
        bridges.append(dict(vendor_material_id=f'VM{i+1:04d}{j+1}',material_id=mat,vendor_id=v['vendor_id'],plant_id=plants[(i+j)%len(plants)][0],contract_id=f'CTR{(i//10)+1:05d}-{j+1}',approved_from=months[(i+j)%15],approved_to='' if (i+j)%17 else '2025-06-30',contract_currency=v['preferred_currency'],quoted_unit_price=n((0.7+(i%53)*0.19)*(1+j*.065)),lead_time_days=15+(i*7+j*11)%65,min_order_qty=[50,100,250,500][i%4],allocation_target_pct=[60,30,10,0][min(j,3)]))
    related=[(main,0.72),('Crude Oil',0.18),('Natural Gas',0.10)]
    if main=='Crude Oil':related=[('Crude Oil',.75),('Natural Gas',.15),('Coal',.10)]
    for commodity,weight in related:
        mappings.append(dict(material_id=mat,commodity_id=commodity_ids[commodity],exposure_weight=weight,lag_months=[0,1,2,3][(i+len(commodity))%4],mapping_confidence=['High','Medium','Low'][i%3],valid_from='2020-01-01'))
rowsave('dim_material.csv',materials)
rowsave('bridge_vendor_material.csv',bridges)
rowsave('bridge_material_commodity.csv',mappings)

# Synthetic market prices have COVID decline, 2021–22 rebound, 2022 energy disruption and trends.
cm=[]; lookup={}
for c in commodities:
    x=base[c]
    for ti,month in enumerate(months):
        y=int(month[:4]);m=int(month[5:7]);
        shock=(.78 if y==2020 and m in (4,5,6) else (1.21 if y==2022 and c in ('Natural Gas','Coal','Crude Oil','Benzene') else 1))
        seasonal=1+.035*math.sin((m-1)*math.pi/6+(len(c)%3))
        x=max(base[c]*.48, x*math.exp(R.gauss(0,.045)+(.003 if ti<40 else -.001)))
        price=n(x*shock*seasonal)
        lookup[(c,month)]=price
        cm.append(dict(commodity_id=commodity_ids[c],month=month,index_price=price,index_currency='USD',index_unit=unit[c],publication_status='Published',benchmark_region=['Global','Europe','Asia'][len(c)%3]))
# A few deliberately missing index points (retain rows with blank values).
for idx in [47,138,251,442,690,864]: cm[idx]['index_price']='';cm[idx]['publication_status']='Missing'
rowsave('fact_commodity_monthly.csv',cm)

# Foreign currency unit: amount of target currency per 1 EUR, monthly reference rate.
fx_base={'EUR':1,'USD':1.11,'INR':84,'TRY':7.5,'CNY':7.8,'VND':25800,'THB':35.5,'IDR':16900,'BRL':4.6}
fx=[];fxlookup={}
for cur,b in fx_base.items():
    v=b
    for ti,month in enumerate(months):
        if cur!='EUR':v*=math.exp(R.gauss(.003 if cur in ('TRY','INR') else .0005,.015 if cur!='TRY' else .055))
        rate=n(v) if v>=.1 else round(v,7)
        fxlookup[(cur,month)]=rate
        fx.append(dict(month=month,from_currency='EUR',to_currency=cur,units_per_eur=rate,rate_type='Monthly average',source_label='SYNTHETIC FX reference'))
rowsave('fact_fx_monthly.csv',fx)

activity=[]; issues=[]; performances=[]; rowid=0
issue_defs={
 'DQ01':('Missing order value','order_value_local','NULL numeric; retained as missing, not zero'),
 'DQ02':('Missing PO quantity','po_qty','Cannot calculate unit price'),
 'DQ03':('GR exceeds PO','gr_qty','Possible timing, returns, unit or reconciliation issue'),
 'DQ04':('Negative goods receipt','gr_qty','Return or reversal; do not discard without event context'),
 'DQ05':('Price spike','order_value_local','Extreme unit-price outlier'),
 'DQ06':('Invalid currency','order_currency','Non-ISO currency code'),
 'DQ07':('Invalid vendor key','vendor_id','FK mismatch requires master-data resolution'),
 'DQ08':('Duplicate business key','vendor_material_id,month','Repeated aggregate row; avoid double counting'),
 'DQ09':('Incorrect quantity unit','po_uom','Unit conversion needed'),
 'DQ10':('Missing month for expected series','vendor_material_id,month','No row exists, not equivalent to zero purchase'),
 'DQ11':('Zero quantity with spend','po_qty,order_value_local','Possible freight, adjustment or posting error'),
 'DQ12':('Delayed GR','gr_qty','PO in month but receipt delayed or unmatched')}
def tag(code, rid, table, key):issues.append(dict(issue_id=f'ISS{len(issues)+1:06d}',issue_code=code,table_name=table,record_id=str(rid),business_key=key,description=issue_defs[code][0],recommended_handling=issue_defs[code][2]))

for k,br in enumerate(bridges):
    mat=materials[int(br['vendor_material_id'][2:6])-1]
    v=next(v for v in vendors if v['vendor_id']==br['vendor_id'])
    famidx=next(i for i,f in enumerate(families) if f[1]==mat['material_group_id'])
    commodity=families[famidx][3]
    baseprice=float(br['quoted_unit_price']); vendor_effect=1+((k%17)-8)*.011
    previous_price=baseprice
    for ti,month in enumerate(months):
        if month<br['approved_from'] or (br['approved_to'] and month>br['approved_to'][:7]+'-01'):continue
        # Some months genuinely have no record; others are explicit zero-activity SAP extracts.
        activity_p=.15 if k%8==0 else (.39 if k%5==0 else .67)
        if ti%12 in (0,1):activity_p*=.78
        if R.random()>.88 and R.random()>(activity_p):continue
        active=R.random()<activity_p
        if not active and R.random()<.28:continue
        qty=0 if not active else round(max(5,R.lognormvariate(6.45, .67))/5)*5
        if active and k%19==0 and ti%17==0:qty=round(qty*.15)
        price=baseprice*(1+.30*math.log(max(0.15,lookup[(commodity,month)]/base[commodity]))) * vendor_effect*(1+.012*math.sin(ti/3.4))
        price=max(.05,price*(1+R.gauss(0,.025)))
        # reflect stickiness rather than a perfect one-to-one commodity pass-through
        price=.62*previous_price+.38*price;previous_price=price
        orderval=round(qty*price,2)
        if qty>0:
            gr=round(qty*([0,.5,.8,.95,1,1,1,1,1,1,1.05][R.randrange(11)]),3)
        else:gr=0
        rowid+=1
        record=dict(procurement_id=f'POA{rowid:07d}',purch_org_id='1001' if br['plant_id'] in ('1001','1002') else '2001',material_7=mat['material_7'],material_id=mat['material_id'],vendor_id=br['vendor_id'],vendor_material_id=br['vendor_material_id'],material_description=mat['material_description'],plant_id=br['plant_id'],material_group_id=mat['material_group_id'],month=month,order_value_local=f'{orderval:.2f}',order_currency=br['contract_currency'],po_qty=f'{qty:.3f}',po_uom=mat['base_uom'],gr_qty=f'{gr:.3f}',gr_uom=mat['base_uom'],unit_price_local=f'{price:.4f}' if qty else '',order_value_eur=f'{(orderval/fxlookup[(br['contract_currency'],month)]):.2f}',is_zero_activity=int(qty==0),source_system='SAP_ECCO_SIM',document_grain='Monthly aggregated PO/GR')
        activity.append(record)
        if qty>0 and R.random()<.018:
            code=R.choice(['DQ01','DQ02','DQ03','DQ04','DQ05','DQ06','DQ07','DQ09','DQ11','DQ12'])
            if code=='DQ01':record['order_value_local']='';record['order_value_eur']=''
            if code=='DQ02':record['po_qty']='';record['unit_price_local']=''
            if code=='DQ03':record['gr_qty']=f'{qty*1.65:.3f}'
            if code=='DQ04':record['gr_qty']=f'{-qty*.25:.3f}'
            if code=='DQ05':record['order_value_local']=f'{orderval*9:.2f}';record['order_value_eur']=f'{orderval*9/fxlookup[(br['contract_currency'],month)]:.2f}'
            if code=='DQ06':record['order_currency']='EURO'
            if code=='DQ07':record['vendor_id']='999999'
            if code=='DQ09':record['po_uom']='PCS' if mat['base_uom']=='PAA' else 'PAA'
            if code=='DQ11':record['po_qty']='0.000';record['unit_price_local']=''
            if code=='DQ12':record['gr_qty']='0.000'
            tag(code,record['procurement_id'],'fact_procurement_monthly.csv',f"{br['vendor_material_id']}|{month}")
        if qty>0 and R.random()<.0015:
            duplicate=record.copy();duplicate['procurement_id']=f'POA{rowid+10000000:07d}'
            activity.append(duplicate);tag('DQ08',duplicate['procurement_id'],'fact_procurement_monthly.csv',f"{br['vendor_material_id']}|{month}")
    # quarterly delivery and quality KPIs; not direct proxies for unobserved purchases
    for qi in range(0,len(months),3):
        sub=months[qi:qi+3]
        performances.append(dict(performance_id=f'PER{k+1:05d}-{qi//3+1:02d}',vendor_id=br['vendor_id'],plant_id=br['plant_id'],quarter_start=sub[0],quarter_end=sub[-1],delivery_lines=R.randint(5,90),on_time_delivery_pct=round(min(100,max(58,93+R.gauss(0,6)-(k%11))),1),defect_rate_pct=round(max(0,R.gauss(1.4,1.2)),2),avg_actual_lead_days=max(5,round(int(br['lead_time_days'])*R.uniform(.85,1.3))),price_variance_pct=round(R.gauss(2,5),2),capacity_utilization_pct=round(R.uniform(40,98),1)))

rowsave('fact_procurement_monthly.csv',activity)
rowsave('fact_vendor_performance_quarterly.csv',performances)
rowsave('data_quality_issue_register.csv',issues)

dictionary=[]
def define(table, specs,grain,primary):
    for field,typ,meaning,nullable in specs:
        dictionary.append(dict(table_name=table,column_name=field,data_type=typ,description=meaning,nullable=nullable,table_grain=grain,primary_key=primary,expected_relationship='See ER diagram',example_value=''))
for table,grain,pk,defs in [
('dim_purchasing_org.csv','One purchasing organization','purch_org_id','purch_org_id:text:Purchasing organization SAP code:N;purch_org_name:text:Organization label:N'),
('dim_plant.csv','One production plant','plant_id','plant_id:text:Plant key:N;plant_name:text:Plant description:N;country_code:text:ISO alpha-2 country:N;local_currency:text:ISO currency:N;purch_org_id:text:Owning purchasing organization FK:N'),
('dim_vendor.csv','One vendor master','vendor_id','vendor_id:text:Vendor key:N;vendor_name:text:Simulated supplier name:N;vendor_country:text:Country code:N;preferred_currency:text:Currency:N;approved_status:text:Approval status:N;payment_terms_days:integer:Payment term days:N;incoterm:text:International trade term:N;vendor_tier:text:Strategic classification:N'),
('dim_material.csv','One full material / SKU','material_id','material_id:text:Full SKU identifier:N;material_7:text:Short material family code:N;material_description:text:SKU description:N;material_group_id:text:SAP-like material group:N;material_group_name:text:Material family:N;base_uom:text:Base quantity unit (PAA pairs, KG kilograms, SQM square meters):N;product_category:text:Product segment:N;active_from:date:Master-data start:N;active_to:date:Master-data end:Y'),
('bridge_vendor_material.csv','One approved vendor–SKU–plant sourcing relationship','vendor_material_id','vendor_material_id:text:Unique relationship key:N;material_id:text:Material FK:N;vendor_id:text:Vendor FK:N;plant_id:text:Plant FK:N;contract_id:text:Illustrative sourcing contract:N;approved_from:date:Approval start:N;approved_to:date:Approval expiry:Y;contract_currency:text:Currency for orders:N;quoted_unit_price:decimal:Illustrative quoted unit rate:N;lead_time_days:integer:Expected lead time:N;min_order_qty:integer:Minimum order quantity:N;allocation_target_pct:integer:Indicative sourcing allocation (not guaranteed to sum to 100 across all periods):N'),
('dim_commodity.csv','One commodity index','commodity_id','commodity_id:text:Commodity key:N;commodity_name:text:Commodity index name:N;index_unit:text:Price measurement unit:N;source_label:text:Simulation disclosure:N;source_type:text:Simulated or observed label:N'),
('bridge_material_commodity.csv','One material–commodity exposure','material_id,commodity_id','material_id:text:Material FK:N;commodity_id:text:Commodity FK:N;exposure_weight:decimal:Model exposure weight (sums to 1 by material):N;lag_months:integer:Assumed lag for commodity effect:N;mapping_confidence:text:Judgment confidence:N;valid_from:date:Mapping effective date:N'),
('fact_commodity_monthly.csv','One commodity per month','commodity_id,month','commodity_id:text:Commodity FK:N;month:date:First calendar day of month:N;index_price:decimal:Synthetic market benchmark price:Y;index_currency:text:Currency (USD):N;index_unit:text:Denominator for price:N;publication_status:text:Available or Missing:N;benchmark_region:text:Index geography:N'),
('fact_fx_monthly.csv','One EUR-to-currency exchange rate per month','month,from_currency,to_currency','month:date:First calendar day of month:N;from_currency:text:Base EUR:N;to_currency:text:Quote currency:N;units_per_eur:decimal:Quote-currency units per one EUR:N;rate_type:text:Monthly average synthetic:N;source_label:text:Simulation disclosure:N'),
('fact_procurement_monthly.csv','One vendor–SKU–plant–month aggregate, except intentional duplicate anomalies','procurement_id','procurement_id:text:Technical row ID:N;purch_org_id:text:Purchasing organization FK:N;material_7:text:Short material key:N;material_id:text:Full SKU FK:N;vendor_id:text:Vendor FK (intentional mismatches exist):N;vendor_material_id:text:Sourcing link FK:N;material_description:text:Denormalized source description:N;plant_id:text:Plant FK:N;material_group_id:text:Group ID:N;month:date:Calendar month:N;order_value_local:decimal:PO value in order_currency:Y;order_currency:text:PO value currency (invalid codes deliberately present):N;po_qty:decimal:Purchase-order quantity:Y;po_uom:text:Purchase order unit:N;gr_qty:decimal:Goods-received quantity may include reversals:N;gr_uom:text:Goods receipt unit:N;unit_price_local:decimal:Nominal contracted currency per base unit:Y;order_value_eur:decimal:EUR-converted value using monthly synthetic FX:Y;is_zero_activity:integer:1 if zero PO quantity originally:N;source_system:text:Simulated SAP-like source:N;document_grain:text:Indicates monthly aggregation:N'),
('fact_vendor_performance_quarterly.csv','Vendor–plant–quarter on sourcing relationships (may have repeated vendor-plant rows)','performance_id','performance_id:text:Record key:N;vendor_id:text:Supplier FK:N;plant_id:text:Plant FK:N;quarter_start:date:Start month:N;quarter_end:date:End month:N;delivery_lines:integer:Observed-like count:N;on_time_delivery_pct:decimal:On-time receipt percent:N;defect_rate_pct:decimal:Defective deliveries percent:N;avg_actual_lead_days:integer:Actual lead-time estimate:N;price_variance_pct:decimal:Price-versus-baseline difference:N;capacity_utilization_pct:decimal:Estimated supplier capacity use:N'),
('data_quality_issue_register.csv','One injected issue annotation','issue_id','issue_id:text:Issue identifier:N;issue_code:text:Issue category:N;table_name:text:Affected file:N;record_id:text:Technical row ID:N;business_key:text:Logical vendor-material and month:N;description:text:Error description:N;recommended_handling:text:Suggested remediation:N')]:
    specs=[(parts[0],parts[1],parts[2],'Yes' if parts[3]=='Y' else 'No') for item in defs.split(';') for parts in [item.split(':')]]
    define(table,specs,grain,pk)
rowsave('data_dictionary.csv',dictionary)

mermaid='''erDiagram
    DIM_PURCHASING_ORG ||--o{ DIM_PLANT : manages
    DIM_PLANT ||--o{ BRIDGE_VENDOR_MATERIAL : supplies_to
    DIM_VENDOR ||--o{ BRIDGE_VENDOR_MATERIAL : offers
    DIM_MATERIAL ||--o{ BRIDGE_VENDOR_MATERIAL : sourced_as
    BRIDGE_VENDOR_MATERIAL ||--o{ FACT_PROCUREMENT_MONTHLY : records
    DIM_VENDOR ||--o{ FACT_VENDOR_PERFORMANCE_QUARTERLY : assessed
    DIM_PLANT ||--o{ FACT_VENDOR_PERFORMANCE_QUARTERLY : receives_at
    DIM_MATERIAL ||--o{ BRIDGE_MATERIAL_COMMODITY : exposed_to
    DIM_COMMODITY ||--o{ BRIDGE_MATERIAL_COMMODITY : influences
    DIM_COMMODITY ||--o{ FACT_COMMODITY_MONTHLY : indexed_by
    FACT_FX_MONTHLY }o--o{ FACT_PROCUREMENT_MONTHLY : converts_currency_month
    DIM_PURCHASING_ORG { string purch_org_id PK }
    DIM_PLANT { string plant_id PK string purch_org_id FK }
    DIM_VENDOR { string vendor_id PK }
    DIM_MATERIAL { string material_id PK string material_7 }
    BRIDGE_VENDOR_MATERIAL { string vendor_material_id PK string material_id FK string vendor_id FK string plant_id FK }
    FACT_PROCUREMENT_MONTHLY { string procurement_id PK string vendor_material_id FK date month decimal order_value_local decimal po_qty decimal gr_qty }
    FACT_VENDOR_PERFORMANCE_QUARTERLY { string performance_id PK string vendor_id FK string plant_id FK date quarter_start }
    DIM_COMMODITY { string commodity_id PK }
    BRIDGE_MATERIAL_COMMODITY { string material_id FK string commodity_id FK decimal exposure_weight }
    FACT_COMMODITY_MONTHLY { string commodity_id FK date month decimal index_price }
    FACT_FX_MONTHLY { date month string from_currency string to_currency decimal units_per_eur }
'''
(OUT/'er_diagram.mmd').write_text(mermaid,encoding='utf-8')

readme=f'''# ECCO-style raw material procurement forecasting — synthetic data package

**IMPORTANT: This is fully synthetic demonstration data, NOT authentic ECCO procurement, vendor, commodity or currency data.** The user-provided sample supplied field conventions, not verified transactions. Supplier names except the illustrative first sample are invented; even that sample is not asserted to be an ECCO supplier. All prices, FX rates, lead times, quality and performance observations are simulated. Do not present model accuracy on this dataset as real-world evidence.

## Scope
- Historical monthly range: **2020-01 through 2026-09**, inclusive (81 months).
- **1,200 SKUs**, **95 vendors**, **6 plants**, **13 commodity indices**; individual SKUs have 2–4 possible vendors.
- Source-like procurement fact reflects order values and PO/GR quantities at **SKU × vendor × plant × month**, with explicit zero months and absent months. PO aggregation is *not* a PO-line transaction ledger.
- Commodity mapping supports material-weighted lag features, and monthly FX enables EUR normalization.
- Vendor performance is synthetic quarterly information. For true production use, aggregate its entries correctly to distinct vendor–plant–quarter records (the sample intentionally models relationship-level observations).

## Files and rows
{chr(10).join(f'- `{k}`: {v:,} rows' for k,v in counts.items())}
- `er_diagram.mmd`: editable Mermaid ER diagram
- `er_diagram.svg`: rendered ER diagram if local rendering available
- `data_dictionary.csv`: all field definitions, keys, types and grains
- `DATA_QUALITY_GUIDE.md`: injection catalogue and interpretation
- `build_ecco_dataset.py`: reproducible generator

## Important joins
1. `fact_procurement_monthly.vendor_material_id` → `bridge_vendor_material.vendor_material_id`, then material, vendor, plant dimensions. In bad rows, fact vendor_id may disagree; use relationship key as canonical but **flag** mismatch.
2. `bridge_material_commodity.material_id` → `dim_material.material_id` and `commodity_id` → `fact_commodity_monthly.commodity_id`; join commodity observations on requested lagged month for time-causal modeling.
3. `fact_fx_monthly`: `month = procurement.month`, `to_currency = procurement.order_currency`, `from_currency = EUR`. Divide local order value by `units_per_eur` to convert to EUR. Do not re-convert existing `order_value_eur`.
4. Procurement unit price: order value / PO quantity where both are valid, and PO qty > 0. Do not treat missing months or zero-PO months as observed price = 0.
5. Vendor quarterly KPIs should be aggregated (weighted by delivery_lines for on-time and defect percentages); lag signals when predicting future months to avoid data leakage.

## Forecasting / data engineering cautions
- Build forecasting panel over **vendor × material × plant × month**, retain `purchased_this_month` and missingness flags. Forecasting **unit price conditional on a purchase** differs from demand / procurement occurrence forecasting.
- Resolve PAA / PCS / KG / SQM unit mismatches before EUR-per-base-unit price comparisons.
- Check vendor contracts' start/end dates and avoid future vendor performance, commodity publication and spot FX leakage.
- The material and vendor master have plausible structural features but are generated with patterns; synthetic data can be used to test ETL, joins, UI and pipeline behavior, not procurement decisions.
- No material-price forecasts are included: all months are simulated historical observations.

## Reproducibility
Run `python3 build_ecco_dataset.py` in the directory above this folder. It deterministically recreates the CSVs (Python 3.10+). The exported records may have intentional discrepancies recorded in the issue register.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
guide='''# Deliberately injected data quality conditions

The dataset contains two kinds of sparse procurement: **explicit zero-quantity monthly rows** and **entirely missing months**. Neither is equivalent to a measured market price of zero.

| Code | Issue | Correct interpretation / suggested rule |
|---|---|---|
'''+''.join(f'| {k} | {v[0]} | {v[2]} |\n' for k,v in issue_defs.items())+'''

Other authentic-looking challenges: supplier changes and contract expirations; variable currencies across vendors; unequal purchase frequency; different base units; time-lagged commodity exposure; receipt delays; seasonality, COVID-period dip and 2022 commodity shocks; no vendor-performance guarantee for every SKU/month.

The issue register records **injected row-level errors**, not a complete output of a data-quality scanner. Run independent checks for duplicates, referential integrity, non-negative metrics, date continuity, contract validity, normalized units and FX consistency. `DQ10` is a **structural missing-month pattern**, so there is no row-level `record_id` to enumerate it; generate the expected panel to detect these gaps. Pricing anomalies can make cached `order_value_eur` and `unit_price_local` disagree with the raw value; treat independently as fields to validate.

Suggested quality KPIs: valid FX join rate, unit price derivation rate on positive-PO rows, missing month rate by vendor–SKU, invalid vendor foreign keys, duplicate natural keys, GR/PO discrepancy ratio, and commodity-index coverage. Document tolerances and remediation ownership before fitting models.
'''
(OUT/'DATA_QUALITY_GUIDE.md').write_text(guide,encoding='utf-8')

manifest={'period_start':months[0],'period_end':months[-1],'sku_count':len(materials),'vendor_count':len(vendors),'vendor_sku_plant_relationships':len(bridges),'commodity_count':len(commodities),'file_row_counts':counts,'issue_counts':dict(Counter(i['issue_code'] for i in issues)),'synthetic':True,'seed':27102026}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
os.makedirs(OUT/'source',exist_ok=True)
import shutil
shutil.copy2(__file__,OUT/'source'/'build_ecco_dataset.py')
target=Path('ECCO_Procurement_Forecasting_Synthetic_Dataset_2020_2026.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for f in OUT.rglob('*'):
        if f.is_file():z.write(f,f.relative_to(OUT.parent))
print(json.dumps({'zip':str(target.resolve()),'zip_bytes':target.stat().st_size,**manifest},indent=2))
