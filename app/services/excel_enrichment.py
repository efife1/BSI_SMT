from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import re
import sqlite3

from app.services.excel_parser import parse_excel

OBSERVATION_FIELDS = (
    "team", "last_lap_vec", "last_lap_ts", "diff_laps", "missing_pre", "missing_post",
    "missing_points_percent", "data_coverage", "rt2_percent", "rt2_tracking", "rt20_percent",
    "rt20_sol_good_percent", "diff_percent", "avg_l1as", "avg_l2as", "avg_l5as",
    "camera_flag", "camera_360_flag", "notes",
)


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).lower())


def _car(value) -> str:
    text = _text(value).lstrip("#").strip()
    return text.upper()


def _vector(value) -> str:
    text = _text(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _flag(value):
    if value is None or value == "":
        return None
    return 1 if _text(value).upper() in {"YES", "Y", "TRUE", "1", "X"} else 0


def _same(a, b) -> bool:
    if a is None and b is None:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return _text(a) == _text(b)


def _audit(conn, entity_type, entity_id, field, old, new, user, action="update"):
    conn.execute(
        "insert into audit_log(entity_type,entity_id,field_name,old_value,new_value,changed_by,reason,action) values(?,?,?,?,?,?,?,?)",
        (entity_type, entity_id, field, _text(old), _text(new), user, "Excel enrichment import", action),
    )


def _find_event(conn: sqlite3.Connection, row: dict):
    exact = conn.execute(
        "select * from events where series=? and race_date=? and lower(trim(track))=lower(trim(?))",
        (row["series"], row.get("race_date"), row.get("track")),
    ).fetchall()
    if len(exact) == 1:
        return exact[0], False
    candidates = conn.execute(
        "select * from events where series=? and race_date=?",
        (row["series"], row.get("race_date")),
    ).fetchall()
    if len(candidates) == 1:
        return candidates[0], False
    normalized = [event for event in candidates if _norm(event["track"]) == _norm(row.get("track"))]
    if len(normalized) == 1:
        return normalized[0], False
    return None, len(candidates) > 1


def _find_observation(conn: sqlite3.Connection, event_id: int, row: dict):
    rows = conn.execute("select * from observations where event_id=?", (event_id,)).fetchall()
    exact = [item for item in rows if _car(item["car_number"]) == _car(row.get("car_number")) and _vector(item["vector"]) == _vector(row.get("vector"))]
    if len(exact) == 1:
        return exact[0], False
    # Leading-zero fallback only when it resolves uniquely.
    def numeric_car(value):
        text = _car(value)
        return text.lstrip("0") or "0"
    fallback = [item for item in rows if numeric_car(item["car_number"]) == numeric_car(row.get("car_number")) and _vector(item["vector"]) == _vector(row.get("vector"))]
    if len(fallback) == 1:
        return fallback[0], False
    return None, len(exact) > 1 or len(fallback) > 1


def enrich_database_from_excel(conn: sqlite3.Connection, path: Path, original_name: str, user: str) -> dict:
    conn.row_factory = sqlite3.Row
    rows = parse_excel(path)
    groups = defaultdict(list)
    for row in rows:
        key = (row.get("series"), row.get("race_date"), _norm(row.get("track")), _car(row.get("car_number")), _vector(row.get("vector")))
        groups[key].append(row)

    report = {
        "source_file": original_name,
        "rows_read": len(rows),
        "groups_read": len(groups),
        "events_matched": set(),
        "events_created": 0,
        "observations_matched": set(),
        "observations_created": 0,
        "observation_fields_updated": 0,
        "event_fields_updated": 0,
        "camera_assignments_added": 0,
        "camera_assignments_updated": 0,
        "rows_unmatched": 0,
        "rows_ambiguous": 0,
        "conflicts": [],
        "unmatched": [],
        "ambiguous": [],
    }

    for group_rows in groups.values():
        representative = group_rows[0]
        event, event_ambiguous = _find_event(conn, representative)
        if not event:
            entry = {k: representative.get(k) for k in ("series", "race_date", "track", "car_number", "vector", "source_sheet", "source_row")}
            if event_ambiguous:
                report["rows_ambiguous"] += len(group_rows); report["ambiguous"].append(entry)
                continue
            if not representative.get("race_date") or not representative.get("track"):
                report["rows_unmatched"] += len(group_rows); report["unmatched"].append(entry)
                continue
            conn.execute(
                "insert into events(series,race_date,track,track_type,data_rate,notes,source_file) values(?,?,?,?,?,?,?)",
                (representative.get("series"), representative.get("race_date"), representative.get("track"),
                 representative.get("track_type"), representative.get("data_rate"), representative.get("notes"), original_name),
            )
            event_id = conn.execute("select last_insert_rowid()").fetchone()[0]
            event = conn.execute("select * from events where id=?", (event_id,)).fetchone()
            _audit(conn, "event", event_id, "event", "", json.dumps(entry), user, "insert")
            report["events_created"] += 1
        report["events_matched"].add(event["id"])

        # Fill event metadata only when the database value is blank.
        for field in ("track_type", "data_rate"):
            incoming = representative.get(field)
            if incoming not in (None, "") and event[field] in (None, ""):
                conn.execute(f"update events set {field}=?,updated_at=current_timestamp where id=?", (incoming, event["id"]))
                _audit(conn, "event", event["id"], field, event[field], incoming, user)
                report["event_fields_updated"] += 1

        observation, observation_ambiguous = _find_observation(conn, event["id"], representative)
        if not observation:
            entry = {k: representative.get(k) for k in ("series", "race_date", "track", "car_number", "vector", "source_sheet", "source_row")}
            if observation_ambiguous:
                report["rows_ambiguous"] += len(group_rows); report["ambiguous"].append(entry)
                continue
            if representative.get("car_number") in (None, "") or representative.get("vector") in (None, ""):
                report["rows_unmatched"] += len(group_rows); report["unmatched"].append(entry)
                continue
            values = {field: representative.get(field) for field in OBSERVATION_FIELDS}
            values["camera_flag"] = _flag(values.get("camera_flag"))
            values["camera_360_flag"] = _flag(values.get("camera_360_flag"))
            columns = ["event_id", "report_row", "car_number", "vector", *OBSERVATION_FIELDS, "original_values_json", "updated_by"]
            payload = [event["id"], representative.get("source_row"), _car(representative.get("car_number")), _vector(representative.get("vector")),
                       *[values.get(field) for field in OBSERVATION_FIELDS], json.dumps(representative, default=str), user]
            placeholders = ",".join("?" for _ in columns)
            conn.execute(f"insert into observations({','.join(columns)}) values({placeholders})", payload)
            observation_id = conn.execute("select last_insert_rowid()").fetchone()[0]
            observation = conn.execute("select * from observations where id=?", (observation_id,)).fetchone()
            _audit(conn, "observation", observation_id, "observation", "", json.dumps(entry), user, "insert")
            report["observations_created"] += 1
        report["observations_matched"].add(observation["id"])

        for field in OBSERVATION_FIELDS:
            incoming = representative.get(field)
            if field in {"camera_flag", "camera_360_flag"}:
                incoming = _flag(incoming)
            current = observation[field]
            if incoming in (None, ""):
                continue
            if current in (None, ""):
                conn.execute(f"update observations set {field}=?,updated_at=current_timestamp,updated_by=? where id=?", (incoming, user, observation["id"]))
                _audit(conn, "observation", observation["id"], field, current, incoming, user)
                report["observation_fields_updated"] += 1
            elif not _same(current, incoming):
                report["conflicts"].append({
                    "observation_id": observation["id"], "field": field,
                    "database_value": current, "spreadsheet_value": incoming,
                    "series": representative.get("series"), "track": representative.get("track"),
                    "car_number": representative.get("car_number"), "vector": representative.get("vector"),
                })

        camera_rows = [r for r in group_rows if _text(r.get("camera_position")).lower() not in {"", "no cameras", "none"}]
        for slot, camera_row in enumerate(camera_rows[:4], start=1):
            serial = _text(camera_row.get("camera_serial")) or None
            if serial and serial.upper() in {"NA", "N/A", "-"}:
                serial = None
            position = _text(camera_row.get("camera_position")) or None
            notes = _text(camera_row.get("notes")) or None
            existing = conn.execute(
                "select * from camera_assignments where observation_id=? and slot_number=?",
                (observation["id"], slot),
            ).fetchone()
            if not existing:
                conn.execute(
                    "insert into camera_assignments(observation_id,slot_number,camera_serial,camera_position,notes,updated_by) values(?,?,?,?,?,?)",
                    (observation["id"], slot, serial, position, notes, user),
                )
                assignment_id = conn.execute("select last_insert_rowid()").fetchone()[0]
                _audit(conn, "camera_assignment", assignment_id, "assignment", "", json.dumps({"serial": serial, "position": position}), user, "insert")
                report["camera_assignments_added"] += 1
            else:
                updates = []
                values = []
                for field, incoming in (("camera_serial", serial), ("camera_position", position), ("notes", notes)):
                    if incoming not in (None, "") and existing[field] in (None, ""):
                        updates.append(f"{field}=?"); values.append(incoming)
                        _audit(conn, "camera_assignment", existing["id"], field, existing[field], incoming, user)
                    elif incoming not in (None, "") and not _same(existing[field], incoming):
                        report["conflicts"].append({
                            "camera_assignment_id": existing["id"], "field": field,
                            "database_value": existing[field], "spreadsheet_value": incoming,
                            "series": representative.get("series"), "track": representative.get("track"),
                            "car_number": representative.get("car_number"), "vector": representative.get("vector"), "slot": slot,
                        })
                if updates:
                    values.extend([user, existing["id"]])
                    conn.execute(f"update camera_assignments set {','.join(updates)},updated_at=current_timestamp,updated_by=? where id=?", values)
                    report["camera_assignments_updated"] += 1

    report["events_matched"] = len(report["events_matched"])
    report["observations_matched"] = len(report["observations_matched"])
    report["conflict_count"] = len(report["conflicts"])
    report["summary"] = (
        f"Excel enrichment: {report['events_created']} events created; {report['observations_created']} observations created; {report['observations_matched']} observations processed; "
        f"{report['observation_fields_updated']} fields filled; "
        f"{report['camera_assignments_added']} camera assignments added; "
        f"{report['camera_assignments_updated']} assignments updated; "
        f"{report['conflict_count']} conflicts preserved for review; "
        f"{report['rows_unmatched']} unmatched rows."
    )
    return report
