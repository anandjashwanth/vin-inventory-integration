"""
VIN-to-inventory integration.

Reads VINs from a CSV file, checks them locally, decodes them in batches through
the NHTSA vPIC API, maps the results into a dealership inventory format and
validates them. Writes three outputs:
  output/inventory_clean.csv      records ready to load into the dealer system
  output/exceptions.csv           records held back, with the reason for each
  output/data_quality_summary.md  decode rate, error codes, missing fields, by region

Usage:
  python src/vin_integration.py                    # live run against the API
  python src/vin_integration.py --offline          # demo run using a saved sample response
  python src/vin_integration.py --input data/my_vins.csv
"""
import argparse
import csv
import json
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
API_BATCH_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/"
BATCH_SIZE = 50          # the API accepts up to 50 VINs per request
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# 1. Local checks, before calling the API
# ---------------------------------------------------------------------------
TRANSLIT = {**{str(d): d for d in range(10)},
            **dict(zip("ABCDEFGH", range(1, 9))),
            **dict(zip("JKLMN", range(1, 6))), "P": 7, "R": 9,
            **dict(zip("STUVWXYZ", range(2, 10)))}
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
ALLOWED = set(TRANSLIT)  # digits and letters except I, O and Q


def region_of(vin: str) -> str:
    """World region from the first character of the VIN (manufacturer code)."""
    c = vin[:1]
    if c in "12345":
        return "North America"
    if c in "STUVWXYZ":
        return "Europe"
    if c in "JKLMNPR":
        return "Asia"
    if c in "6789":
        return "Oceania / South America"
    if c in "ABCDEFGH":
        return "Africa"
    return "Unknown"


def expected_check_digit(vin: str) -> str:
    total = sum(TRANSLIT[ch] * w for ch, w in zip(vin, WEIGHTS))
    r = total % 11
    return "X" if r == 10 else str(r)


def local_check(vin: str):
    """Return (ok, issue). Catches problems without spending an API call."""
    if len(vin) != 17:
        return False, f"Wrong length ({len(vin)} characters, expected 17)"
    bad = sorted(set(vin) - ALLOWED)
    if bad:
        return False, f"Invalid characters: {', '.join(bad)} (I, O and Q are never used in VINs)"
    # The check digit (9th character) is mandatory for North American vehicles only.
    if region_of(vin) == "North America" and vin[8] != expected_check_digit(vin):
        return False, f"Check digit fails (9th character is {vin[8]}, expected {expected_check_digit(vin)})"
    return True, ""


# ---------------------------------------------------------------------------
# 2. Calling the API
# ---------------------------------------------------------------------------
def decode_batch(vins):
    """POST up to 50 VINs; retry with back-off on network errors."""
    payload = {"format": "json", "data": ";".join(vins)}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(API_BATCH_URL, data=payload, timeout=TIMEOUT_SECONDS)
            r.raise_for_status()
            return r.json()["Results"]
        except (requests.RequestException, KeyError, ValueError) as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"API call failed after {MAX_RETRIES} attempts: {exc}")
            time.sleep(2 ** attempt)


def decode_all(vins, offline=False):
    if offline:
        sample = json.loads((ROOT / "tests/fixtures/sample_response.json").read_text())["Results"]
        by_vin = {row["VIN"]: row for row in sample}
        return [by_vin.get(v, {"VIN": v, "ErrorCode": "8", "ErrorText": "Not in offline sample"}) for v in vins]
    results = []
    for i in range(0, len(vins), BATCH_SIZE):
        results.extend(decode_batch(vins[i:i + BATCH_SIZE]))
        time.sleep(1)  # be polite to a free public service
    return results


# ---------------------------------------------------------------------------
# 3. Mapping API fields to the dealer inventory format
# ---------------------------------------------------------------------------
def load_mapping():
    with open(ROOT / "docs/03_data_mapping.csv", newline="") as f:
        return list(csv.DictReader(f))


def transform(value, rule):
    value = (value or "").strip()
    if value == "" or value.lower() == "not applicable":
        return ""
    if rule == "upper":
        return value.upper()
    if rule == "title":
        return value.title()
    if rule == "int":
        try:
            return str(int(float(value)))
        except ValueError:
            return ""
    if rule == "decimal_1dp":
        try:
            return f"{float(value):.1f}"
        except ValueError:
            return ""
    return value


def map_record(api_row, mapping):
    return {m["target_field"]: transform(api_row.get(m["source_field"]), m["transform"]) for m in mapping}


# ---------------------------------------------------------------------------
# 4. Validation after decoding
# ---------------------------------------------------------------------------
def error_codes(api_row):
    raw = str(api_row.get("ErrorCode", "")).strip()
    return [c.strip() for c in raw.split(",") if c.strip()]


# The 9th-character check digit is a North American rule. The API still applies it to
# European VINs and returns code 1, which would wrongly reject valid European vehicles.
IGNORED_CODES_BY_REGION = {"Europe": {"1"}}


def validate(record, api_row, mapping):
    issues = []
    ignore = IGNORED_CODES_BY_REGION.get(record.get("region", ""), set())
    codes = [c for c in error_codes(api_row) if c != "0" and c not in ignore]
    # The API returns HTTP 200 even when decoding fails: the real result is in ErrorCode.
    if codes:
        texts = [t.strip() for t in str(api_row.get("ErrorText", "")).split(";") if t.strip()]
        relevant = [t for t in texts if t.split(" ")[0] in codes] or texts
        issues.append(f"API error code {','.join(codes)}: {' / '.join(relevant)}")
    for m in mapping:
        if m["required"].lower() == "yes" and not record[m["target_field"]]:
            issues.append(f"Missing required field: {m['target_field']}")
    year = record.get("model_year")
    if year and not (1981 <= int(year) <= date.today().year + 1):
        issues.append(f"Model year {year} outside plausible range")
    return issues


# ---------------------------------------------------------------------------
# 5. Run end to end and write outputs
# ---------------------------------------------------------------------------
def run(input_path, offline=False):
    mapping = load_mapping()
    with open(input_path, newline="") as f:
        vins = [row["vin"].strip().upper() for row in csv.DictReader(f) if row.get("vin", "").strip()]

    clean, exceptions, to_decode = [], [], []
    stats = defaultdict(Counter)

    for vin in vins:
        stats["region"][region_of(vin)] += 1
        ok, issue = local_check(vin)
        if ok:
            to_decode.append(vin)
        else:
            exceptions.append({"vin": vin, "stage": "Local check", "issues": issue})
            stats["local_fail"][region_of(vin)] += 1

    for api_row in decode_all(to_decode, offline):
        vin = api_row.get("VIN", "").upper()
        record = map_record(api_row, mapping)
        record["vin"] = vin
        record["region"] = region_of(vin)
        issues = validate(record, api_row, mapping)
        for code in error_codes(api_row) or ["0"]:
            stats["error_code"][code] += 1
        for m in mapping:
            if not record[m["target_field"]]:
                stats["missing"][m["target_field"]] += 1
        if issues:
            exceptions.append({"vin": vin, "stage": "After decode", "issues": " | ".join(issues)})
            stats["decode_fail"][record["region"]] += 1
        else:
            clean.append(record)
            stats["clean"][record["region"]] += 1

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    fields = ["vin", "region"] + [m["target_field"] for m in mapping]
    with open(out / "inventory_clean.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(clean)
    with open(out / "exceptions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["vin", "stage", "issues"])
        w.writeheader()
        w.writerows(exceptions)
    write_summary(out / "data_quality_summary.md", len(vins), len(to_decode), clean, exceptions, stats, offline)
    print(f"{len(vins)} VINs | {len(clean)} clean | {len(exceptions)} exceptions | see output/")


def pct(a, b):
    return f"{(100 * a / b):.0f}%" if b else "n/a"


def write_summary(path, total, decoded, clean, exceptions, stats, offline):
    lines = ["# Data quality summary", ""]
    if offline:
        lines += ["> Offline demo run using a saved sample response. Run without `--offline` for real results.", ""]
    lines += [
        f"- VINs received: **{total}**",
        f"- Rejected by local checks before any API call: **{total - decoded}** ({pct(total - decoded, total)})",
        f"- Sent to the API: **{decoded}**",
        f"- Clean records ready to load: **{len(clean)}** ({pct(len(clean), total)} of all VINs)",
        f"- Exceptions held back for review: **{len(exceptions)}**",
        "",
        "## Results by region",
        "",
        "| Region | VINs | Clean | Clean rate |",
        "|---|---|---|---|",
    ]
    for region, n in stats["region"].most_common():
        c = stats["clean"][region]
        lines.append(f"| {region} | {n} | {c} | {pct(c, n)} |")
    lines += ["", "## API error codes", "", "| Code | Count |", "|---|---|"]
    for code, n in sorted(stats["error_code"].items()):
        lines.append(f"| {code} | {n} |")
    lines += ["", "## Fields most often missing after decode", "", "| Field | Missing |", "|---|---|"]
    for field, n in stats["missing"].most_common(10):
        lines.append(f"| {field} | {n} of {decoded} |")
    Path(path).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Decode, map and validate VINs for a dealership inventory.")
    p.add_argument("--input", default=str(ROOT / "data/vins.csv"))
    p.add_argument("--offline", action="store_true", help="use the saved sample response instead of the live API")
    a = p.parse_args()
    run(a.input, a.offline)
