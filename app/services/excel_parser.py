from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import re

import pandas as pd

SERIES = {"NCS", "NCTS", "NOAPS"}

MAP = {
    "race date": "race_date", "track": "track", "track type": "track_type",
    "series": "series", "car #": "car_number", "carid": "car_number",
    "car number": "car_number", "team": "team", "camera position": "camera_position",
    "camera serial #": "camera_serial", "camera serial": "camera_serial", "vector": "vector",
    "lastlap(vec)": "last_lap_vec", "last lap(vec)": "last_lap_vec",
    "lastlap(t&s)": "last_lap_ts", "last lap(t&s)": "last_lap_ts",
    "difflaps": "diff_laps", "missingpoints_preerdp": "missing_pre",
    "missingpoints_posterdp": "missing_post", "missingpoints_total": "missing_total",
    "missingpoints(%)": "missing_points_percent", "datacoverage(%)": "data_coverage",
    "rt2percent(%)": "rt2_percent", "rt2tracking(%)": "rt2_tracking",
    "rt20percent(%)": "rt20_percent", "rt20solgoodpercent(%)": "rt20_sol_good_percent",
    "diffpercent(%)": "diff_percent", "avgl1as": "avg_l1as", "avgl2as": "avg_l2as",
    "avgl5as": "avg_l5as", "camera": "camera_flag", "360cam": "camera_360_flag",
    "data rate": "data_rate", "notes": "notes",
}


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _clean(value: object):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value.strip() if isinstance(value, str) else value


def _date(value: object) -> str | None:
    value = _clean(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Excel's 1900 date system. Pandas normally converts this already, but
        # this fallback supports workbooks where the date cells are general numbers.
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()
    text = str(value).strip()
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:
        return text


def parse_excel(path: Path) -> list[dict]:
    sheets = pd.read_excel(path, sheet_name=None, dtype=object)
    output: list[dict] = []
    for sheet_name, frame in sheets.items():
        rename = {column: MAP[norm(column)] for column in frame.columns if norm(column) in MAP}
        frame = frame.rename(columns=rename)
        sheet_series = sheet_name.strip().upper()
        for index, source_row in frame.iterrows():
            row = {key: _clean(value) for key, value in source_row.items() if key in MAP.values()}
            row["race_date"] = _date(row.get("race_date"))
            row["series"] = str(row.get("series") or sheet_series).strip().upper()
            row["source_sheet"] = sheet_name
            row["source_row"] = int(index) + 2
            if row["series"] not in SERIES:
                continue
            if not any(row.get(field) not in (None, "") for field in ("track", "car_number", "vector")):
                continue
            output.append(row)
    return output
