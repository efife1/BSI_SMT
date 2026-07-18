from __future__ import annotations

import json
from math import atanh, tanh, sqrt
from statistics import mean, median, pstdev
from typing import Any

try:
    from scipy.stats import pearsonr
except Exception:  # pragma: no cover
    pearsonr = None

FORMULA_VERSION = "2.2.0"
NUMERIC_FACTORS = [
    ("data_coverage", "Data Coverage"),
    ("missing_points_percent", "Missing Points %"),
    ("avg_l1as", "Avg L1AS"),
    ("avg_l2as", "Avg L2AS"),
    ("avg_l5as", "Avg L5AS"),
    ("rt2_percent", "RT2Percent"),
]

def sf(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def allrows(c):
    return [dict(r) for r in c.execute("""
      select o.*,e.series,e.race_date,e.track,e.track_type,
             ca.camera_serial,ca.camera_position
      from observations o join events e on e.id=o.event_id
      left join camera_assignments ca on ca.observation_id=o.id
    """)]

def overview(c,th=95):
    v=[sf(r['rt2_tracking']) for r in allrows(c)];v=[x for x in v if x is not None]
    if not v:return {'count':0,'mean':None,'median':None,'minimum':None,'maximum':None,'stddev':None,'failures':0,'failure_rate':None,'threshold':th}
    f=sum(x<th for x in v)
    return {'count':len(v),'mean':round(mean(v),2),'median':round(median(v),2),'minimum':round(min(v),2),'maximum':round(max(v),2),'stddev':round(pstdev(v),2),'failures':f,'failure_rate':round(100*f/len(v),2),'threshold':th}

def _pearson_details(rows,field):
    pairs=[(sf(r.get(field)),sf(r.get('rt2_tracking'))) for r in rows]
    pairs=[p for p in pairs if None not in p]
    n=len(pairs)
    if n<3:return {'r':None,'p_value':None,'ci_low':None,'ci_high':None,'n':n}
    xs=[p[0] for p in pairs];ys=[p[1] for p in pairs]
    if len(set(xs))<2 or len(set(ys))<2:return {'r':None,'p_value':None,'ci_low':None,'ci_high':None,'n':n}
    if pearsonr:
        result=pearsonr(xs,ys)
        r=float(result.statistic);p=float(result.pvalue)
    else:
        mx=mean(xs);my=mean(ys);dx=[x-mx for x in xs];dy=[y-my for y in ys]
        den=sqrt(sum(x*x for x in dx)*sum(y*y for y in dy));r=sum(a*b for a,b in zip(dx,dy))/den;p=None
    if n>3 and abs(r)<1:
        zr=atanh(r);se=1/sqrt(n-3)
        lo=tanh(zr-1.96*se);hi=tanh(zr+1.96*se)
    else:lo=hi=None
    return {'r':r,'p_value':p,'ci_low':lo,'ci_high':hi,'n':n}

def correlations(c):
    rows=allrows(c);out=[]
    for f,l in NUMERIC_FACTORS:
        d=_pearson_details(rows,f);r=d['r'];a=abs(r or 0)
        s='strong' if a>=.7 else 'moderate' if a>=.4 else 'weak' if a>=.2 else 'minimal' if r is not None else 'insufficient'
        out.append({'field':f,'label':l,'correlation':None if r is None else round(r,4),'sample_count':d['n'],'strength':s,
                    'p_value':None if d['p_value'] is None else round(d['p_value'],6),
                    'ci_low':None if d['ci_low'] is None else round(d['ci_low'],4),
                    'ci_high':None if d['ci_high'] is None else round(d['ci_high'],4)})
    return sorted(out,key=lambda x:abs(x['correlation'] or 0),reverse=True)

def trend(c):
    return [dict(r) for r in c.execute("select e.id,e.race_date,e.series,e.track,round(avg(o.rt2_tracking),2) avg_rt2,count(*) samples,sum(case when o.rt2_tracking<95 then 1 else 0 end) failures from events e join observations o on o.event_id=e.id group by e.id order by e.race_date")]

def rank(c,f,n=3):
    if f in ('series','track'):q=f"select e.{f} label,count(*) samples,round(avg(o.rt2_tracking),2) avg_rt2,round(min(o.rt2_tracking),2) worst_rt2,round(100.0*sum(case when o.rt2_tracking<95 then 1 else 0 end)/count(*),2) failure_rate from events e join observations o on o.event_id=e.id where e.{f} is not null group by e.{f} having count(*)>=? order by avg_rt2"
    elif f in ('camera_serial','camera_position'):q=f"select ca.{f} label,count(*) samples,round(avg(o.rt2_tracking),2) avg_rt2,round(min(o.rt2_tracking),2) worst_rt2,round(100.0*sum(case when o.rt2_tracking<95 then 1 else 0 end)/count(*),2) failure_rate from camera_assignments ca join observations o on o.id=ca.observation_id where ca.{f} is not null and trim(ca.{f})<>'' group by ca.{f} having count(*)>=? order by avg_rt2"
    else:q=f"select o.{f} label,count(*) samples,round(avg(o.rt2_tracking),2) avg_rt2,round(min(o.rt2_tracking),2) worst_rt2,round(100.0*sum(case when o.rt2_tracking<95 then 1 else 0 end)/count(*),2) failure_rate from observations o where o.{f} is not null and trim(o.{f})<>'' group by o.{f} having count(*)>=? order by avg_rt2"
    return [dict(r) for r in c.execute(q,(n,))]

def adjusted(c,f,n=3):
    return [dict(r) for r in c.execute(f"with a as(select event_id,avg(rt2_tracking)m from observations group by event_id),b as(select o.{f} label,o.rt2_tracking-a.m d from observations o join a on a.event_id=o.event_id where o.{f} is not null) select label,count(*) samples,round(avg(d),2) avg_event_adjusted,round(min(d),2) worst_event_adjusted from b group by label having count(*)>=? order by avg_event_adjusted",(n,))]

def _bucket(score):
    return 'strong_evidence' if score>=75 else 'possible_contributors' if score>=50 else 'insufficient_data'

def rootcause(c,oid):
    row=c.execute("select o.*,e.series,e.race_date,e.track from observations o join events e on e.id=o.event_id where o.id=?",(oid,)).fetchone()
    if not row:return None
    r=dict(row)
    event_values=[sf(x[0]) for x in c.execute('select rt2_tracking from observations where event_id=? and rt2_tracking is not null',(r['event_id'],))]
    event_values=[x for x in event_values if x is not None]
    ea=mean(event_values) if event_values else None
    esd=pstdev(event_values) if len(event_values)>1 else None
    delta=(sf(r['rt2_tracking'])-ea) if ea is not None and sf(r['rt2_tracking']) is not None else None
    zscore=(delta/esd) if delta is not None and esd not in (None,0) else None
    result={'formula_version':FORMULA_VERSION,'observation':r,'event_average':round(ea,2) if ea is not None else None,
            'event_stddev':round(esd,4) if esd is not None else None,'event_delta':round(delta,2) if delta is not None else None,
            'event_zscore':round(zscore,4) if zscore is not None else None,
            'strong_evidence':[],'possible_contributors':[],'insufficient_data':[],'calculations':[]}
    result['calculations'].append({'name':'Event-relative RT2','formula':'Delta = RT2 observation - event mean',
      'substitution':f"{r['rt2_tracking']} - {round(ea,4) if ea is not None else 'N/A'}",'result':round(delta,4) if delta is not None else None,
      'inputs':{'observation_rt2':r['rt2_tracking'],'event_mean':ea,'event_samples':len(event_values)}})
    result['calculations'].append({'name':'Event z-score','formula':'z = (RT2 observation - event mean) / event standard deviation',
      'substitution':f"({r['rt2_tracking']} - {round(ea,4) if ea is not None else 'N/A'}) / {round(esd,4) if esd is not None else 'N/A'}",
      'result':round(zscore,4) if zscore is not None else None,'inputs':{'event_stddev':esd}})
    # Event-relative evidence score.
    if delta is not None:
        deviation_component=min(abs(min(delta,0))/12,1)
        z_component=min(abs(min(zscore or 0,0))/3,1)
        score=round(60*deviation_component+40*z_component,2)
        item={'factor':'Event-relative performance','score':score,'evidence':f"RT2 was {abs(delta):.2f} points {'below' if delta<0 else 'above'} event average; z={zscore:.2f}." if zscore is not None else f"RT2 delta was {delta:.2f} points.",
              'math':f"60×{deviation_component:.4f} + 40×{z_component:.4f} = {score:.2f}"}
        result[_bucket(score)].append(item)
    # Numeric contributors, with fully displayed score components.
    allr=allrows(c)
    for field,label in NUMERIC_FACTORS:
        val=sf(r.get(field));stats=_pearson_details(allr,field)
        fleet=[sf(x.get(field)) for x in allr];fleet=[x for x in fleet if x is not None]
        if val is None or not fleet or stats['r'] is None:
            result['insufficient_data'].append({'factor':label,'score':0,'evidence':'Missing value or fewer than three valid paired observations.','math':'Not calculated.'});continue
        fleet_mean=mean(fleet);fleet_sd=pstdev(fleet) if len(fleet)>1 else 0
        standardized=(val-fleet_mean)/fleet_sd if fleet_sd else 0
        adverse=max(0,-stats['r']*standardized)
        correlation_component=min(abs(stats['r']),1)
        deviation_component=min(adverse/2,1)
        repeatability_component=1 if stats['p_value'] is not None and stats['p_value']<0.05 else .5 if stats['p_value'] is not None and stats['p_value']<0.10 else .2
        sample_component=min(stats['n']/30,1)
        quality_component=min(stats['n']/max(len(allr),1),1)
        score=round(30*correlation_component+25*deviation_component+20*repeatability_component+15*sample_component+10*quality_component,2)
        item={'factor':label,'score':score,
          'evidence':f"Value {val:.3f}; fleet mean {fleet_mean:.3f}; r={stats['r']:.4f}; p={stats['p_value']:.6f}; n={stats['n']}.",
          'math':f"30×{correlation_component:.4f} + 25×{deviation_component:.4f} + 20×{repeatability_component:.4f} + 15×{sample_component:.4f} + 10×{quality_component:.4f} = {score:.2f}"}
        result[_bucket(score)].append(item)
        result['calculations'].append({'name':f'{label} Pearson correlation','formula':'r = sum((x-xbar)(y-ybar)) / sqrt(sum((x-xbar)^2) sum((y-ybar)^2))',
          'substitution':f"r={stats['r']:.6f}, n={stats['n']}, p={stats['p_value'] if stats['p_value'] is not None else 'N/A'}",
          'result':round(stats['r'],6),'inputs':{'selected_value':val,'fleet_mean':fleet_mean,'fleet_stddev':fleet_sd,'ci95':[stats['ci_low'],stats['ci_high']]}})
    # Repeated car/vector evidence.
    for field,label in [('vector','Vector'),('car_number','Car')]:
        value=r.get(field)
        if not value:continue
        s=c.execute(f'select count(*) n,avg(rt2_tracking) a,100.0*sum(case when rt2_tracking<95 then 1 else 0 end)/count(*) fr from observations where {field}=? and rt2_tracking is not null',(value,)).fetchone()
        n=s['n'];avg=s['a'];fr=s['fr'];repeat=min(n/10,1);failure=min((fr or 0)/100,1);under=min(max(95-(avg or 95),0)/15,1);score=round(40*under+35*failure+25*repeat,2)
        item={'factor':f'{label} {value}','score':score,'evidence':f"{n} samples average {avg:.2f}% RT2; {fr:.1f}% below 95%.",
              'math':f"40×{under:.4f} + 35×{failure:.4f} + 25×{repeat:.4f} = {score:.2f}"}
        result[_bucket(score)].append(item)
        result['calculations'].append({'name':f'{label} repeated performance','formula':'score = 40 underperformance + 35 failure rate + 25 repeatability',
          'substitution':item['math'],'result':score,'inputs':{'samples':n,'average_rt2':avg,'failure_rate':fr}})
    for bucket in ('strong_evidence','possible_contributors','insufficient_data'):
        result[bucket]=sorted(result[bucket],key=lambda x:x.get('score',0),reverse=True)
    return result

def save_analysis_snapshot(c,event_id=None,source='automatic import'):
    payload={'overview':overview(c,95),'correlations':correlations(c),'event_id':event_id,'formula_version':FORMULA_VERSION}
    cur=c.execute('insert into analysis_runs(event_id,formula_version,source,results_json) values(?,?,?,?)',(event_id,FORMULA_VERSION,source,json.dumps(payload,default=str)))
    return cur.lastrowid
