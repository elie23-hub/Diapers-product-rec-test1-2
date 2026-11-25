# -*- coding: utf-8 -*-
"""Live progress for recruitment, product test 1, and product test 2."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CITY = {"1": "Riyadh", "2": "Jeddah", "3": "Other"}
NATIONALITY = {"1": "Saudi", "2": "Expat Arab", "3": "Other"}
AGE_BRACKET = {
    "1": "Below 20",
    "2": "20–25",
    "3": "26–30",
    "4": "31–40",
    "5": "41–50",
    "6": "Above 50",
}
USAGE = {
    "1": "Used all period",
    "2": "Used another product",
}

# First failing recruitment gate, in questionnaire order.
# A placed respondent is one who reached a continuing income answer (S12 = 2–7).
# That question is hidden unless every earlier screen has already passed.


def load_dotenv_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


FORM_UIDS = {
    "RECRUIT_UID": "aERGJXaoW5Y6KDQmhxfecM",
    "T1_UID": "aHq4p5zHhTUcZrnGxW5vrx",
    "T2_UID": "akb8ozyxmkgCHxmuYUSMgw",
}


def get_config() -> dict[str, str]:
    cfg = dict(FORM_UIDS)
    cfg["KOBO_BASE"] = "https://kf.kobotoolbox.org"
    cfg.update(load_dotenv_file(ROOT / ".env"))
    for key in ("KOBO_TOKEN", "KOBO_BASE", "RECRUIT_UID", "T1_UID", "T2_UID"):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    if not cfg.get("KOBO_TOKEN"):
        raise RuntimeError("Missing config: KOBO_TOKEN")
    return cfg


def kobo_get(cfg: dict[str, str], path: str) -> dict:
    url = f"{cfg['KOBO_BASE'].rstrip('/')}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {cfg['KOBO_TOKEN']}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_submissions(cfg: dict[str, str], uid: str) -> list[dict]:
    results: list[dict] = []
    start = 0
    page = 500
    while True:
        query = urllib.parse.urlencode({"format": "json", "limit": page, "start": start})
        data = kobo_get(cfg, f"/api/v2/assets/{uid}/data/?{query}")
        batch = data.get("results") or []
        results.extend(batch)
        total = int(data.get("count") or 0)
        start += len(batch)
        if not batch or start >= total:
            break
    return results


def norm_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    return " ".join(text.split())


def norm_id(value) -> str | None:
    text = norm_text(value)
    return text.casefold() if text else None


def field(row: dict, name: str):
    if name in row and row[name] not in (None, ""):
        return row[name]
    suffix = "/" + name
    for key, value in row.items():
        if str(key).endswith(suffix) and value not in (None, ""):
            return value
    return None


def code(value) -> str | None:
    text = norm_text(value)
    if text is None:
        return None
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def choice_set(value) -> set[str]:
    if value is None or value == "":
        return set()
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value).replace(",", " ").split()
    return {c for c in (code(part) for part in parts) if c}


def as_int(value) -> int | None:
    text = code(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def as_float(value) -> float | None:
    text = code(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def stamp(row: dict) -> str:
    return str(row.get("_submission_time") or row.get("end") or "")


def screen_reason(row: dict) -> str | None:
    """Return the first screen-out, or None when the respondent is placed."""
    selected = choice_set(field(row, "S1"))
    if selected != {"6"}:
        return "Industry"

    age = as_int(field(row, "S2_age"))
    bracket = code(field(row, "S2"))
    if age is None or age < 20 or age > 50 or bracket not in {"2", "3", "4", "5"}:
        return "Age"

    if code(field(row, "S3")) != "2":
        return "Recent research"

    if code(field(row, "S4")) != "1":
        return "Gender"

    if code(field(row, "S5")) not in {"1", "2"}:
        return "Nationality"

    if code(field(row, "S6")) not in {"1", "2"}:
        return "City"

    if code(field(row, "S7")) != "1":
        return "No diaper-age child"

    babies = as_int(field(row, "S8"))
    if babies not in {1, 2, 3, 4}:
        return "Baby count"

    for index in range(1, babies + 1):
        brand = code(field(row, f"brand_{index}"))
        size = code(field(row, f"size_{index}"))
        if brand is None or size is None:
            return "Baby details"
        if brand not in {"1", "2"}:
            return "Other brand"
        if size not in {"5", "6"}:
            return "Diaper size"

    if code(field(row, "S10")) != "2":
        return "Baby allergy"

    if code(field(row, "S11")) not in {"3", "4", "5", "6", "7"}:
        return "Education"

    if code(field(row, "S12")) not in {"2", "3", "4", "5", "6", "7"}:
        return "Income"

    return None


def latest_by_id(rows: list[dict]) -> tuple[dict[str, dict], int]:
    grouped: dict[str, dict] = {}
    missing = 0
    for row in rows:
        rid = norm_id(field(row, "id"))
        if not rid:
            missing += 1
            continue
        current = grouped.get(rid)
        if current is None or stamp(row) >= stamp(current):
            grouped[rid] = row
    return grouped, missing


def product_view(rows: list[dict], passed_ids: set[str]) -> dict:
    by_id, missing_id = latest_by_id(rows)
    used_all = used_other = leakage = allergy = satisfied = would_buy = 0
    scores: list[float] = []
    matched = 0
    for rid, row in by_id.items():
        if rid in passed_ids:
            matched += 1
        usage = code(field(row, "T4"))
        if usage == "1":
            used_all += 1
        elif usage == "2":
            used_other += 1
        if code(field(row, "Q7a")) == "1":
            leakage += 1
        if code(field(row, "Q7c")) == "1":
            allergy += 1
        if code(field(row, "Q1")) in {"1", "2"}:
            satisfied += 1
        if code(field(row, "Q3")) in {"4", "5"}:
            would_buy += 1
        score = as_float(field(row, "Q4"))
        if score is not None:
            scores.append(score)
    unique = len(by_id)
    return {
        "rows": len(rows),
        "unique_ids": unique,
        "matched_passed": matched,
        "unmatched": unique - matched,
        "missing_id": missing_id,
        "used_all": used_all,
        "used_other": used_other,
        "leakage": leakage,
        "allergy": allergy,
        "satisfied": satisfied,
        "would_buy": would_buy,
        "avg_performance": round(sum(scores) / len(scores), 1) if scores else None,
    }


def person_record(rid: str, recruit: dict | None, t1: dict | None, t2: dict | None) -> dict:
    reason = screen_reason(recruit) if recruit else None
    passed = recruit is not None and reason is None
    city_code = code(field(recruit, "S6")) if recruit else None
    nation_code = code(field(recruit, "S5")) if recruit else None
    bracket = code(field(recruit, "S2")) if recruit else None

    def usage(row: dict | None) -> str:
        if row is None:
            return ""
        return USAGE.get(code(field(row, "T4")) or "", "Submitted")

    if passed:
        stage = "passed"
        recruitment = "Passed"
    elif recruit is not None:
        stage = "screened"
        recruitment = reason or "Screened out"
    else:
        stage = "product_only"
        recruitment = "No recruitment record"

    return {
        "id": (norm_text(field(recruit or t1 or t2 or {}, "id")) or rid),
        "name": norm_text(field(recruit or t1 or t2 or {}, "respondent_name")) or "",
        "phone": norm_text(field(recruit or t1 or t2 or {}, "phone")) or "",
        "interviewer": norm_text(field(recruit or {}, "Interviewer_Name")) or "" if recruit else "",
        "city": CITY.get(city_code or "", ""),
        "nationality": NATIONALITY.get(nation_code or "", ""),
        "age_bracket": AGE_BRACKET.get(bracket or "", ""),
        "recruitment": recruitment,
        "stage": stage,
        "product_1": "Submitted" if t1 else "Not yet",
        "product_1_usage": usage(t1),
        "product_2": "Submitted" if t2 else "Not yet",
        "product_2_usage": usage(t2),
        "both": bool(t1 and t2),
        "passed": passed,
    }


def build_from_rows(recruit_rows: list[dict], t1_rows: list[dict], t2_rows: list[dict]) -> dict:
    recruit_by_id, recruit_missing = latest_by_id(recruit_rows)
    duplicate_ids = 0
    seen: dict[str, int] = {}
    for row in recruit_rows:
        rid = norm_id(field(row, "id"))
        if not rid:
            continue
        seen[rid] = seen.get(rid, 0) + 1
    duplicate_ids = sum(1 for count in seen.values() if count > 1)

    passed_ids = {rid for rid, row in recruit_by_id.items() if screen_reason(row) is None}
    screened_ids = set(recruit_by_id) - passed_ids

    reason_counts: dict[str, int] = {}
    for rid in screened_ids:
        reason = screen_reason(recruit_by_id[rid]) or "Screened out"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    reason_order = [
        "Industry",
        "Age",
        "Recent research",
        "Gender",
        "Nationality",
        "City",
        "No diaper-age child",
        "Baby count",
        "Baby details",
        "Other brand",
        "Diaper size",
        "Baby allergy",
        "Education",
        "Income",
    ]
    screen_reasons = [
        {"label": label, "count": reason_counts[label]}
        for label in reason_order
        if reason_counts.get(label)
    ]

    t1 = product_view(t1_rows, passed_ids)
    t2 = product_view(t2_rows, passed_ids)
    t1_by_id, _ = latest_by_id(t1_rows)
    t2_by_id, _ = latest_by_id(t2_rows)

    both_ids = {rid for rid in passed_ids if rid in t1_by_id and rid in t2_by_id}
    passed_city = {"Riyadh": 0, "Jeddah": 0, "Other": 0}
    both_city = {"Riyadh": 0, "Jeddah": 0, "Other": 0}
    passed_nation = {"Saudi": 0, "Expat Arab": 0, "Other": 0}
    for rid in passed_ids:
        city = CITY.get(code(field(recruit_by_id[rid], "S6")) or "", "Other")
        nation = NATIONALITY.get(code(field(recruit_by_id[rid], "S5")) or "", "Other")
        passed_city[city] = passed_city.get(city, 0) + 1
        passed_nation[nation] = passed_nation.get(nation, 0) + 1
        if rid in both_ids:
            both_city[city] = both_city.get(city, 0) + 1

    roster = []
    all_ids = set(recruit_by_id) | set(t1_by_id) | set(t2_by_id)
    for rid in all_ids:
        roster.append(person_record(rid, recruit_by_id.get(rid), t1_by_id.get(rid), t2_by_id.get(rid)))

    def sort_key(person: dict):
        rank = {"passed": 0, "product_only": 1, "screened": 2}[person["stage"]]
        if person["stage"] == "passed" and not person["both"]:
            rank = -1
        return (rank, person["id"])

    roster.sort(key=sort_key)
    passed_n = len(passed_ids)
    waiting_t1 = sum(1 for rid in passed_ids if rid not in t1_by_id)
    waiting_t2 = sum(1 for rid in passed_ids if rid not in t2_by_id)

    def share(part: int) -> float:
        return round(100.0 * part / passed_n, 1) if passed_n else 0.0

    return {
        "recruitment_rows": len(recruit_rows),
        "recruitment_ids": len(recruit_by_id),
        "passed": passed_n,
        "screened_out": len(screened_ids),
        "missing_recruitment_id": recruit_missing,
        "duplicate_ids": duplicate_ids,
        "passed_riyadh": passed_city["Riyadh"],
        "passed_jeddah": passed_city["Jeddah"],
        "passed_saudi": passed_nation["Saudi"],
        "passed_expat": passed_nation["Expat Arab"],
        "saudi_share": share(passed_nation["Saudi"]),
        "expat_share": share(passed_nation["Expat Arab"]),
        "both": len(both_ids),
        "both_riyadh": both_city["Riyadh"],
        "both_jeddah": both_city["Jeddah"],
        "product_1_done": t1["matched_passed"],
        "product_2_done": t2["matched_passed"],
        "waiting_t1": waiting_t1,
        "waiting_t2": waiting_t2,
        "product_1": t1,
        "product_2": t2,
        "screen_reasons": screen_reasons,
        "roster": roster,
    }


def build_stats() -> dict:
    cfg = get_config()
    recruit_rows = fetch_all_submissions(cfg, cfg["RECRUIT_UID"])
    t1_rows = fetch_all_submissions(cfg, cfg["T1_UID"])
    t2_rows = fetch_all_submissions(cfg, cfg["T2_UID"])
    payload = build_from_rows(recruit_rows, t1_rows, t2_rows)
    payload.update({
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Live from Kobo",
    })
    return payload


def build_stats_safe() -> tuple[dict, int]:
    try:
        return build_stats(), 200
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"Kobo HTTP {exc.code}", "detail": detail[:500]}, 502
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}, 500


def _check(label: str, row: dict, expected: str | None) -> None:
    got = screen_reason(row)
    if got != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {got!r}")


def self_test() -> None:
    base = {
        "S1": "6",
        "S2_age": 30,
        "S2": "3",
        "S3": "2",
        "S4": "1",
        "S5": "1",
        "S6": "1",
        "S7": "1",
        "S8": "1",
        "baby_1/brand_1": "1",
        "baby_1/size_1": "5",
        "S10": "2",
        "S11": "6",
        "S12": "3",
    }
    _check("placed", base, None)
    _check("industry", {**base, "S1": "1 6"}, "Industry")
    _check("age low", {**base, "S2_age": 18, "S2": ""}, "Age")
    _check("research", {**base, "S3": "1"}, "Recent research")
    _check("gender", {**base, "S4": "2"}, "Gender")
    _check("nation", {**base, "S5": "3"}, "Nationality")
    _check("city", {**base, "S6": "3"}, "City")
    _check("child", {**base, "S7": "2"}, "No diaper-age child")
    _check("brand", {**base, "baby_1/brand_1": "3"}, "Other brand")
    _check("size", {**base, "baby_1/size_1": "4"}, "Diaper size")
    _check("allergy", {**base, "S10": "1"}, "Baby allergy")
    _check("education", {**base, "S11": "1"}, "Education")
    _check("income", {**base, "S12": "1"}, "Income")
    _check("income refuse", {**base, "S12": "8"}, "Income")
    two = {
        **base,
        "S8": "2",
        "baby_2/brand_2": "2",
        "baby_2/size_2": "3",
    }
    _check("second baby size", two, "Diaper size")

    recruit = [
        {**base, "id": "A1", "S12": "8", "_submission_time": "2026-01-01T00:00:00"},
        {**base, "id": "A2", "S12": "1", "respondent_name": "Two", "_submission_time": "2026-01-01T00:00:00"},
        {**base, "id": "A1", "respondent_name": "One", "S6": "2", "_submission_time": "2026-01-02T00:00:00"},
    ]
    t1 = [{"id": "A1", "T4": "1", "Q7a": "2", "Q7c": "2", "Q1": "1", "Q3": "5", "Q4": "8"}]
    t2 = [{"id": "A1", "T4": "2", "Q7a": "1", "Q7c": "1", "Q1": "4", "Q4": "6"}, {"id": "B9", "T4": "1"}]
    stats = build_from_rows(recruit, t1, t2)
    assert stats["passed"] == 1, stats["passed"]
    assert stats["screened_out"] == 1
    assert stats["duplicate_ids"] == 1
    assert stats["both"] == 1
    assert stats["both_jeddah"] == 1
    assert stats["product_2"]["unmatched"] == 1
    assert stats["product_1"]["used_all"] == 1
    assert stats["product_2"]["leakage"] == 1
    assert stats["waiting_t1"] == 0
    print("self-test ok")


if __name__ == "__main__":
    self_test()
