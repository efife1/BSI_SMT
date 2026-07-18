from __future__ import annotations
from collections import defaultdict
from statistics import mean, pstdev
from typing import Any

SERIES = ("NCS", "NCTS", "NOAPS")
FORMULA_VERSION = "3.0.0"

def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def detect_series(filename: str) -> str | None:
    import re
    name=(filename or "").upper()
    for series in ("NOAPS","NCTS","NCS"):
        if re.search(rf"(?:^|[^A-Z0-9]){series}(?:[^A-Z0-9]|$)", name):
            return series
    if "DAYTONA 500" in name:
        return "NCS"
    return None

def series_rows(c, series: str):
    return [dict(r) for r in c.execute("""
      SELECT o.*,e.series,e.race_date,e.track,
             ca.camera_serial,ca.camera_position,ca.slot_number
      FROM observations o JOIN events e ON e.id=o.event_id
      LEFT JOIN camera_assignments ca ON ca.observation_id=o.id
      WHERE e.series=?
    """,(series,))]

def series_overview(c, series: str, threshold: float=95):
    vals=[fnum(r['rt2_tracking']) for r in series_rows(c,series)]
    vals=[v for v in vals if v is not None]
    if not vals:return {'count':0,'mean':None,'median':None,'minimum':None,'maximum':None,'stddev':None,'failures':0,'failure_rate':None}
    from statistics import median
    failures=sum(v<threshold for v in vals)
    return {'count':len(vals),'mean':round(mean(vals),2),'median':round(median(vals),2),'minimum':round(min(vals),2),'maximum':round(max(vals),2),'stddev':round(pstdev(vals),2),'failures':failures,'failure_rate':round(100*failures/len(vals),2)}

def _event_means(c,series):
    return {r['event_id']:r['avg_rt2'] for r in c.execute("""
      SELECT o.event_id,AVG(o.rt2_tracking) avg_rt2
      FROM observations o JOIN events e ON e.id=o.event_id
      WHERE e.series=? AND o.rt2_tracking IS NOT NULL GROUP BY o.event_id
    """,(series,))}

def recurring_offenders(c, series: str, threshold: float=95, minimum_samples: int=3, limit: int=250):
    if series not in SERIES: raise ValueError('Series must be NCS, NCTS, or NOAPS')
    rows=series_rows(c,series); event_means=_event_means(c,series)
    series_vals=[]; seen=set()
    for r in rows:
        if r['id'] in seen:continue
        seen.add(r['id']);v=fnum(r['rt2_tracking'])
        if v is not None:series_vals.append(v)
    series_mean=mean(series_vals) if series_vals else None
    dimensions=[
      ('Vector',('vector',)),('Car',('car_number',)),('Camera',('camera_serial',)),
      ('Vector + Car',('vector','car_number')),('Camera + Vector',('camera_serial','vector')),
      ('Camera + Car',('camera_serial','car_number')),('Camera + Position',('camera_serial','camera_position')),
      ('Vector + Car + Camera',('vector','car_number','camera_serial')),
    ]
    results=[]
    for type_name,fields in dimensions:
        groups=defaultdict(list)
        for r in rows:
            vals=tuple(str(r.get(f) or '').strip() for f in fields)
            if any(not v for v in vals):continue
            groups[vals].append(r)
        for vals,items in groups.items():
            unique={}
            camera_dimension='camera_serial' in fields or 'camera_position' in fields
            for item in items:
                key=(item['id'],item.get('camera_serial') if camera_dimension else None)
                unique[key]=item
            items=list(unique.values())
            rt2=[fnum(x['rt2_tracking']) for x in items];rt2=[v for v in rt2 if v is not None]
            if len(rt2)<minimum_samples:continue
            events=len({x['event_id'] for x in items});failures=sum(v<threshold for v in rt2)
            failure_rate=100*failures/len(rt2);avg=mean(rt2)
            deltas=[fnum(x['rt2_tracking'])-event_means[x['event_id']] for x in items if fnum(x['rt2_tracking']) is not None and x['event_id'] in event_means]
            event_adjusted=mean(deltas) if deltas else None
            failure_events=len({x['event_id'] for x in items if fnum(x['rt2_tracking']) is not None and fnum(x['rt2_tracking'])<threshold})
            under=min(max((threshold-avg)/15,0),1); fail=failure_rate/100; repeat=min(events/8,1); adj=min(max(-(event_adjusted or 0)/10,0),1)
            score=round(35*under+30*fail+20*repeat+15*adj,2)
            results.append({'type':type_name,'key':' + '.join(vals),'values':dict(zip(fields,vals)),'samples':len(rt2),'events':events,'failure_events':failure_events,
              'avg_rt2':round(avg,2),'worst_rt2':round(min(rt2),2),'failure_rate':round(failure_rate,2),'series_mean':round(series_mean,2) if series_mean is not None else None,
              'series_delta':round(avg-series_mean,2) if series_mean is not None else None,'event_adjusted':round(event_adjusted,2) if event_adjusted is not None else None,
              'evidence_score':score,'classification':'strong' if score>=75 else 'possible' if score>=50 else 'watch',
              'math':f'35×{under:.4f} + 30×{fail:.4f} + 20×{repeat:.4f} + 15×{adj:.4f} = {score:.2f}'})
    results.sort(key=lambda x:(-x['evidence_score'],x['avg_rt2']))
    return results[:limit]

def offender_detail(c,series,type_name,key):
    item=next((x for x in recurring_offenders(c,series,minimum_samples=1,limit=10000) if x['type']==type_name and x['key']==key),None)
    if not item:return None
    clauses=['e.series=?'];params=[series]
    for field,value in item['values'].items():
        alias='ca' if field in {'camera_serial','camera_position'} else 'o'
        clauses.append(f'{alias}.{field}=?');params.append(value)
    history=[dict(r) for r in c.execute(f"""
      SELECT e.race_date,e.track,o.car_number,o.vector,o.rt2_tracking,o.data_coverage,
             o.missing_points_percent,o.avg_l1as,o.avg_l2as,o.avg_l5as,
             ca.camera_serial,ca.camera_position
      FROM observations o JOIN events e ON e.id=o.event_id
      LEFT JOIN camera_assignments ca ON ca.observation_id=o.id
      WHERE {' AND '.join(clauses)} ORDER BY e.race_date
    """,params)]
    return {'summary':item,'history':history}

def observation_series_evidence(c,oid):
    row=c.execute("SELECT o.*,e.series,e.race_date,e.track FROM observations o JOIN events e ON e.id=o.event_id WHERE o.id=?",(oid,)).fetchone()
    if not row:return None
    row=dict(row); series=row['series']
    event=[fnum(r[0]) for r in c.execute('SELECT rt2_tracking FROM observations WHERE event_id=? AND rt2_tracking IS NOT NULL',(row['event_id'],))]
    event=[v for v in event if v is not None]; emean=mean(event) if event else None; esd=pstdev(event) if len(event)>1 else None
    delta=fnum(row['rt2_tracking'])-emean if emean is not None and fnum(row['rt2_tracking']) is not None else None
    z=delta/esd if delta is not None and esd not in (None,0) else None
    camera_serials={r[0] for r in c.execute('SELECT camera_serial FROM camera_assignments WHERE observation_id=? AND camera_serial IS NOT NULL',(oid,))}
    matches=[]
    for item in recurring_offenders(c,series,minimum_samples=2,limit=10000):
        ok=True
        for field,value in item['values'].items():
            if field=='camera_serial':ok &= value in camera_serials
            else:ok &= str(row.get(field) or '')==value
        if ok:matches.append(item)
    return {'formula_version':FORMULA_VERSION,'observation':row,'event_average':round(emean,2) if emean is not None else None,'event_stddev':round(esd,4) if esd is not None else None,
      'event_delta':round(delta,2) if delta is not None else None,'event_zscore':round(z,4) if z is not None else None,'series_offenders':matches[:30],
      'calculations':[{'name':'Event-relative RT2','formula':'Δ = RT2 observation − event mean','substitution':f"{row['rt2_tracking']} − {round(emean,4) if emean is not None else 'N/A'}",'result':round(delta,4) if delta is not None else None},
                      {'name':'Event z-score','formula':'z = (RT2 observation − event mean) / event standard deviation','substitution':f"({row['rt2_tracking']} − {round(emean,4) if emean is not None else 'N/A'}) / {round(esd,4) if esd is not None else 'N/A'}",'result':round(z,4) if z is not None else None}]}
