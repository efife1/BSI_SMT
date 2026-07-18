from pathlib import Path
import pandas as pd,re
MAP={"race date":"race_date","track":"track","track type":"track_type","team":"team","carid":"car_number","car number":"car_number","vector":"vector",
"camera position":"camera_position","camera serial #":"camera_serial","camera serial":"camera_serial","data rate":"data_rate",
"rt2percent":"rt2_percent","rt2percent (%)":"rt2_percent","rt2tracking":"rt2_tracking","rt2tracking (%)":"rt2_tracking",
"datacoverage":"data_coverage","datacoverage (%)":"data_coverage","missingpoints":"missing_post","missingpoints (%)":"missing_points_percent",
"avgl1as":"avg_l1as","avgl2as":"avg_l2as","avgl5as":"avg_l5as","notes":"notes"}
def norm(x):return re.sub(r"\s+"," ",str(x).strip().lower())
def parse_excel(path:Path):
 sheets=pd.read_excel(path,sheet_name=None,dtype=object)
 out=[]
 for name,df in sheets.items():
  ren={c:MAP[norm(c)] for c in df.columns if norm(c) in MAP};df=df.rename(columns=ren)
  for i,row in df.iterrows():
   r={k:(None if pd.isna(v) else v) for k,v in row.items()}
   r["series"]=name.upper() if name.upper() in {"NCS","NCTS","NOAPS"} else r.get("series")
   out.append(r)
 return out
