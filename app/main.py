from pathlib import Path
import datetime,hashlib,json,os,shutil,sqlite3,uuid
from fastapi import FastAPI,Request,UploadFile,File,Form,HTTPException,Depends
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.pdf_parser import parse_pdf
from app.services.excel_parser import parse_excel
from app.services.excel_enrichment import enrich_database_from_excel
from app.services.analytics import overview,correlations,trend,rank,adjusted,rootcause,save_analysis_snapshot
from database.migrate import migrate
from app.services.series_analytics import SERIES,detect_series,series_overview,recurring_offenders,dashboard_top_offenders,offender_detail,observation_series_evidence

APP=FastAPI(title="BSI SMT",version="3.1.1")
APPDIR=Path(__file__).parent;DATA=Path("data");DB=DATA/"bsi_smt_v2.db";UP=DATA/"uploads";AR=DATA/"archive"
UP.mkdir(parents=True,exist_ok=True);AR.mkdir(parents=True,exist_ok=True)
APP.mount("/static",StaticFiles(directory=APPDIR/"static"),name="static");tpl=Jinja2Templates(directory=APPDIR/"templates")

def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute("pragma foreign_keys=on");return c

def valid_session(request):
 u=request.cookies.get("bsi_user");token=request.cookies.get("bsi_token")
 expected=hashlib.sha256((os.getenv("APP_USERNAME","admin")+os.getenv("APP_PASSWORD","")).encode()).hexdigest()
 return u==os.getenv("APP_USERNAME","admin") and token==expected

def auth(request:Request):
 if not valid_session(request):raise HTTPException(401,"Unauthorized")
 return request.cookies.get("bsi_user")

@APP.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException):
 if exc.status_code==401 and not request.url.path.startswith('/api/') and request.url.path!='/login':
  return RedirectResponse('/login',303)
 return JSONResponse({'detail':exc.detail},status_code=exc.status_code)

@APP.on_event("startup")
def startup():
 migrate(DB, make_backup=False)

@APP.get("/login",response_class=HTMLResponse)
def login_page(request:Request):
 if valid_session(request):return RedirectResponse('/',303)
 return tpl.TemplateResponse("login.html",{"request":request})

@APP.post("/login")
def login(username:str=Form(...),password:str=Form(...)):
 if username!=os.getenv("APP_USERNAME","admin") or password!=os.getenv("APP_PASSWORD",""):raise HTTPException(401,"Invalid login")
 r=RedirectResponse("/",303);r.set_cookie("bsi_user",username,httponly=True,samesite="lax");r.set_cookie("bsi_token",hashlib.sha256((username+password).encode()).hexdigest(),httponly=True,samesite="lax");return r

@APP.get("/",response_class=HTMLResponse)
def home(request:Request,series:str="NCS",threshold:float=95,minimum_samples:int=3,user=Depends(auth)):
 if series not in SERIES:series="NCS"
 minimum_samples=max(1,min(minimum_samples,100))
 with db() as c:
  s=dict(c.execute("select * from v_dashboard").fetchone())
  health=dashboard_top_offenders(c,series,threshold,minimum_samples,5)
  series_stats=series_overview(c,series,threshold)
 return tpl.TemplateResponse("dashboard.html",{"request":request,"s":s,"series":series,"series_options":SERIES,"threshold":threshold,"minimum_samples":minimum_samples,"health":health,"series_stats":series_stats})

@APP.get("/import",response_class=HTMLResponse)
def imp_page(request:Request,user=Depends(auth)):return tpl.TemplateResponse("import.html",{"request":request})

async def save_upload(f):
 p=UP/f"{uuid.uuid4().hex}-{Path(f.filename or 'upload.pdf').name}"
 with open(p,"wb") as o:
  while b:=await f.read(1048576):o.write(b)
 return p

def import_saved_file(p,original_name,auto_analyze=True):
 migrate(DB, make_backup=False)
 fh=hashlib.sha256(p.read_bytes()).hexdigest()
 with db() as c:
  if c.execute("select 1 from imports where file_hash=?",(fh,)).fetchone():
   p.unlink(missing_ok=True);return {'filename':original_name,'status':'duplicate','rows_inserted':0}
  suffix=p.suffix.lower()
  if suffix in {'.xlsx','.xlsm'}:
   result=enrich_database_from_excel(c,p,original_name,user='spreadsheet-import')
   c.execute("insert into imports(source_file,file_hash,status,rows_read,rows_inserted,rows_skipped,message) values(?,?,?,?,?,?,?)",(original_name,fh,'complete',result['rows_read'],result['events_created']+result['observations_created']+result['event_fields_updated']+result['observation_fields_updated']+result['camera_assignments_added']+result['camera_assignments_updated'],result['rows_unmatched']+result['rows_ambiguous'],json.dumps(result)))
   c.commit()
   archive=AR/f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{p.name}";shutil.move(p,archive)
   return {'filename':original_name,'status':'complete','import_type':'excel-enrichment','rows_inserted':result['events_created']+result['observations_created']+result['event_fields_updated']+result['observation_fields_updated']+result['camera_assignments_added']+result['camera_assignments_updated'],'message':result['summary'],'reconciliation':result}
  if suffix!='.pdf':
   p.unlink(missing_ok=True);return {'filename':original_name,'status':'failed','message':'Supported files are PDF, XLSX, and XLSM.'}
  parsed=parse_pdf(p);e=parsed['event'];detected=detect_series(original_name);e['series']=detected or e.get('series')
  if e.get('series') not in SERIES: raise ValueError('Could not detect series from filename. Include NCS, NCTS, or NOAPS in the filename.')
  c.execute("insert or ignore into events(series,race_date,track,data_rate,notes,source_file) values(?,?,?,?,?,?)",(e['series'],e['race_date'],e['track'],e['data_rate'],e['notes'],original_name))
  event=c.execute("select id from events where series is ? and race_date is ? and track is ?",(e['series'],e['race_date'],e['track'])).fetchone()
  if not event:raise ValueError('Could not resolve imported event')
  event_id=event[0];ins=0
  for r in parsed['rows']:
   try:
    c.execute("""insert into observations(event_id,report_row,car_number,vector,last_lap_vec,last_lap_ts,diff_laps,missing_pre,missing_post,diff_pre_post,missing_points_percent,data_coverage,rt2_percent,rt2_tracking,rt20_percent,rt20_sol_good_percent,diff_percent,avg_l1as,avg_l2as,avg_l5as,camera_flag,camera_360_flag,original_values_json)
    values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(event_id,r['report_row'],r['car_number'],str(r['vector']),r['last_lap_vec'],r['last_lap_ts'],r['diff_laps'],r['missing_pre'],r['missing_post'],r['diff_pre_post'],r['missing_points_percent'],r['data_coverage'],r['rt2_percent'],r['rt2_tracking'],r['rt20_percent'],r['rt20_sol_good_percent'],r['diff_percent'],r['avg_l1as'],r['avg_l2as'],r['avg_l5as'],r['camera_flag'],r['camera_360_flag'],json.dumps(r)));ins+=1
   except sqlite3.IntegrityError:pass
  c.execute("insert into imports(source_file,file_hash,status,rows_read,rows_inserted,message) values(?,?,?,?,?,?)",(original_name,fh,'complete',len(parsed['rows']),ins,'PDF batch import'))
  analysis_id=save_analysis_snapshot(c,event_id,'automatic import') if auto_analyze else None
  c.commit()
 archive=AR/f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{p.name}";shutil.move(p,archive)
 return {'filename':original_name,'status':'complete','event_id':event_id,'rows_read':len(parsed['rows']),'rows_inserted':ins,'analysis_run_id':analysis_id}

@APP.post('/api/preview')
async def preview(file:UploadFile=File(...),user=Depends(auth)):
 p=await save_upload(file)
 try:return parse_pdf(p)
 finally:p.unlink(missing_ok=True)

@APP.post('/api/import')
async def do_import(file:UploadFile=File(...),auto_analyze:bool=Form(True),user=Depends(auth)):
 p=await save_upload(file)
 try:return import_saved_file(p,file.filename,auto_analyze)
 except Exception as exc:
  p.unlink(missing_ok=True);raise HTTPException(400,str(exc))

@APP.post('/api/import/batch')
async def batch_import(files:list[UploadFile]=File(...),auto_analyze:bool=Form(True),user=Depends(auth)):
 results=[]
 for f in files:
  p=None
  try:
   p=await save_upload(f);results.append(import_saved_file(p,f.filename,auto_analyze))
  except Exception as exc:
   if p:p.unlink(missing_ok=True)
   results.append({'filename':f.filename,'status':'failed','message':str(exc)})
 return {'status':'complete','files_received':len(files),'imported':sum(x['status']=='complete' for x in results),'duplicates':sum(x['status']=='duplicate' for x in results),'failed':sum(x['status']=='failed' for x in results),'results':results}

@APP.get('/events',response_class=HTMLResponse)
def events(request:Request,user=Depends(auth)):
 with db() as c:rows=[dict(x) for x in c.execute('select * from events order by race_date desc')]
 return tpl.TemplateResponse('events.html',{'request':request,'events':rows})

@APP.get('/events/{eid}',response_class=HTMLResponse)
def event(request:Request,eid:int,user=Depends(auth)):
 with db() as c:
  er=c.execute('select * from events where id=?',(eid,)).fetchone()
  if not er:raise HTTPException(404,'Event not found')
  e=dict(er);rows=[dict(x) for x in c.execute('select * from observations where event_id=? order by cast(car_number as integer),car_number',(eid,))]
  for r in rows:r['assignments']=[dict(x) for x in c.execute('select * from camera_assignments where observation_id=? order by slot_number',(r['id'],))]
 return tpl.TemplateResponse('event.html',{'request':request,'event':e,'rows':rows})

@APP.post('/api/observations/{oid}')
async def update_obs(oid:int,request:Request,user=Depends(auth)):
 p=await request.json();allowed={'car_number','team','vector','rt2_tracking','notes'}
 with db() as c:
  old=c.execute('select * from observations where id=?',(oid,)).fetchone()
  for f,v in p.items():
   if f in allowed and str(old[f] or '')!=str(v or ''):
    c.execute(f'update observations set {f}=?,updated_at=current_timestamp,updated_by=? where id=?',(v,user,oid));c.execute('insert into audit_log(entity_type,entity_id,field_name,old_value,new_value,changed_by) values(?,?,?,?,?,?)',('observation',oid,f,str(old[f] or ''),str(v or ''),user))
  c.commit()
 return {'saved':True}

@APP.put('/api/observations/{oid}/camera/{slot}')
async def camera(oid:int,slot:int,request:Request,user=Depends(auth)):
 p=await request.json()
 with db() as c:
  c.execute("""insert into camera_assignments(observation_id,slot_number,camera_serial,camera_position,notes,updated_by)
  values(?,?,?,?,?,?) on conflict(observation_id,slot_number) do update set camera_serial=excluded.camera_serial,camera_position=excluded.camera_position,notes=excluded.notes,updated_at=current_timestamp,updated_by=excluded.updated_by""",(oid,slot,p.get('camera_serial'),p.get('camera_position'),p.get('notes'),user));c.commit()
 return {'saved':True}

@APP.get('/analytics',response_class=HTMLResponse)
def analytics(request:Request,threshold:float=95,series:str='NCS',user=Depends(auth)):
 if series not in SERIES:series='NCS'
 with db() as c:
  return tpl.TemplateResponse('analytics.html',{'request':request,'series':series,'series_options':SERIES,
   'ov':series_overview(c,series,threshold),'corr':correlations(c),'trend':[x for x in trend(c) if x['series']==series],
   'vectors':rank(c,'vector')[:20],'cars':rank(c,'car_number')[:20],'cameras':rank(c,'camera_serial')[:20]})

@APP.get('/equipment',response_class=HTMLResponse)
def equipment(request:Request,group:str='vector',minimum_samples:int=3,series:str='NCS',user=Depends(auth)):
 if group not in {'series','track','car_number','vector','camera_serial','camera_position'}:group='vector'
 if series not in SERIES:series='NCS'
 with db() as c:
  rows=rank(c,group,minimum_samples)
  if group!='series':
   # rank() is retained for compatibility; v3's detailed series-specific analysis is on /offenders.
   pass
 return tpl.TemplateResponse('equipment.html',{'request':request,'rows':rows,'group':group,'minimum_samples':minimum_samples,'series':series,'series_options':SERIES})

@APP.get('/offenders',response_class=HTMLResponse)
def offenders_page(request:Request,series:str='NCS',minimum_samples:int=3,threshold:float=95,user=Depends(auth)):
 if series not in SERIES:series='NCS'
 with db() as c:rows=recurring_offenders(c,series,threshold,minimum_samples,250)
 return tpl.TemplateResponse('offenders.html',{'request':request,'rows':rows,'series':series,'series_options':SERIES,'minimum_samples':minimum_samples,'threshold':threshold})

@APP.get('/offenders/detail',response_class=HTMLResponse)
def offender_detail_page(request:Request,series:str,type:str,key:str,user=Depends(auth)):
 if series not in SERIES:raise HTTPException(400,'Invalid series')
 with db() as c:result=offender_detail(c,series,type,key)
 if not result:raise HTTPException(404,'Offender not found')
 return tpl.TemplateResponse('offender_detail.html',{'request':request,'result':result,'series':series})

@APP.get('/root-cause',response_class=HTMLResponse)
def rc(request:Request,series:str='NCS',event_id:int|None=None,observation_id:int|None=None,user=Depends(auth)):
 if series not in SERIES:series='NCS'
 with db() as c:
  ev=[dict(x) for x in c.execute('select * from events where series=? order by race_date desc',(series,))]
  obs=[dict(x) for x in c.execute('select id,car_number,vector,rt2_tracking from observations where event_id=? order by cast(car_number as integer)',(event_id,))] if event_id else []
  result=observation_series_evidence(c,observation_id) if observation_id else None
 return tpl.TemplateResponse('root_cause.html',{'request':request,'series':series,'series_options':SERIES,'events':ev,'observations':obs,'selected_event':event_id,'selected_observation':observation_id,'result':result})

@APP.get('/api/offenders/{series}')
def offenders_api(series:str,minimum_samples:int=3,threshold:float=95,user=Depends(auth)):
 if series not in SERIES:raise HTTPException(400,'Invalid series')
 with db() as c:return recurring_offenders(c,series,threshold,minimum_samples,500)

@APP.get('/api/root-cause/{oid}')
def rc_api(oid:int,user=Depends(auth)):
 with db() as c:
  result=observation_series_evidence(c,oid)
  if not result:raise HTTPException(404,'Observation not found')
  return result

app=APP
