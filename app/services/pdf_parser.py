from pathlib import Path
import re,datetime,pdfplumber
COLS=["report_row","car_number","vector","last_lap_vec","last_lap_ts","diff_laps","missing_pre","missing_post",
"diff_pre_post","missing_points_percent","data_coverage","rt2_percent","rt2_tracking","rt20_percent",
"rt20_sol_good_percent","diff_percent","avg_l1as","avg_l2as","avg_l5as","camera_flag","camera_360_flag"]
def parse_pdf(path:Path):
 text="";rows=[]
 with pdfplumber.open(path) as pdf:
  for page in pdf.pages:
   tx=page.extract_text(x_tolerance=2,y_tolerance=3) or "";text+="\n"+tx
   for line in tx.splitlines():
    p=" ".join(line.split()).split()
    if len(p)>=21 and p[0].isdigit():
     try:
      r=dict(zip(COLS,p[:21]))
      for k in ["report_row","vector","last_lap_vec","last_lap_ts","diff_laps","missing_pre","missing_post","diff_pre_post"]:r[k]=int(float(r[k]))
      for k in ["missing_points_percent","data_coverage","rt2_percent","rt2_tracking","rt20_percent","rt20_sol_good_percent","diff_percent","avg_l1as","avg_l2as","avg_l5as"]:r[k]=float(r[k])
      r["camera_flag"]=1 if r["camera_flag"].upper()=="YES" else 0;r["camera_360_flag"]=1 if r["camera_360_flag"].upper()=="YES" else 0
      rows.append(r)
     except:pass
 m=re.search(r"Race\s+(NCS|NCTS|NOAPS)\s*-\s*([A-Za-z]+)\s+(\d+)",text,re.I)
 ty=re.search(r"SMT Tracking Report\s+(.+?)\s+(20\d{2})",text,re.I)
 series=m.group(1).upper() if m else None;track=ty.group(1).strip() if ty else path.stem.split("_")[0]
 date=datetime.datetime.strptime(f"{m.group(2)} {m.group(3)} {ty.group(2)}","%B %d %Y").date().isoformat() if m and ty else None
 rate=re.search(r"Dat[ea]\s+Rate:\s*([0-9.]+)",text,re.I)
 notes=re.search(r"Notes:\s*(.*)$",text,re.I|re.S)
 return {"event":{"series":series,"race_date":date,"track":track,"data_rate":float(rate.group(1)) if rate else None,
 "notes":" ".join(notes.group(1).split()) if notes else ""},"rows":rows,"warnings":[] if rows else ["No rows extracted"]}
