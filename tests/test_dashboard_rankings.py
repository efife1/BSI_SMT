import sqlite3
from app.services.series_analytics import dashboard_top_offenders
from database.migrate import migrate


def test_dashboard_returns_requested_categories(tmp_path):
    db_path=tmp_path/'test.db'
    migrate(db_path,make_backup=False)
    with sqlite3.connect(db_path) as c:
        c.row_factory=sqlite3.Row
        event_id=c.execute("INSERT INTO events(series,race_date,track) VALUES('NCS','2026-01-01','Test')").lastrowid
        for index in range(1,7):
            oid=c.execute("INSERT INTO observations(event_id,report_row,car_number,vector,rt2_tracking) VALUES(?,?,?,?,?)",
                          (event_id,index,str(index),'205',80+index)).lastrowid
            c.execute("INSERT INTO camera_assignments(observation_id,slot_number,camera_serial,camera_position) VALUES(?,?,?,?)",
                      (oid,1,'CAM-LOW','Roof'))
        c.commit()
        result=dashboard_top_offenders(c,'NCS',95,3,5)
    assert set(result)=={'cameras','vectors','cars'}
    assert result['cameras'][0]['key']=='CAM-LOW'
    assert result['vectors'][0]['key']=='205'
    assert len(result['cars'])==0  # each car only appears once and minimum_samples is 3
