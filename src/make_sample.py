"""
Build data/vins.csv from a Kaggle used-car file that has 'vin' and 'make' columns.

Picks a reproducible random sample: half European manufacturers, half others,
plus three VINs broken on purpose to test the local checks.

Usage:
  python src/make_sample.py path\\to\\car_prices.csv
  python src/make_sample.py path\\to\\car_prices.csv --size 200
"""
import argparse
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EUROPEAN_MAKES = {"bmw", "mercedes-benz", "volkswagen", "audi", "volvo", "land rover",
                  "porsche", "mini", "jaguar", "fiat", "smart", "saab"}
BROKEN = [
    ("1HGCM82633A00435", "Broken on purpose: 16 characters"),
    ("1HGCM82633A0O4352", "Broken on purpose: letter O instead of zero"),
    ("1HGCM82633A004353", "Broken on purpose: check digit fails"),
]


def main(source, size, seed):
    european, other, seen = [], [], set()
    with open(source, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        cols = {c.lower().strip(): c for c in reader.fieldnames}
        if "vin" not in cols or "make" not in cols:
            raise SystemExit(f"File needs 'vin' and 'make' columns. Found: {reader.fieldnames}")
        for row in reader:
            vin = (row[cols["vin"]] or "").strip().upper()
            make = (row[cols["make"]] or "").strip()
            if len(vin) != 17 or vin in seen or not make:
                continue
            seen.add(vin)
            (european if make.lower() in EUROPEAN_MAKES else other).append((vin, make))

    rng = random.Random(seed)
    half = size // 2
    picked = rng.sample(european, min(half, len(european))) + rng.sample(other, min(size - half, len(other)))
    rng.shuffle(picked)

    out = ROOT / "data/vins.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vin", "note"])
        for vin, make in picked:
            w.writerow([vin, make])
        w.writerows(BROKEN)
    print(f"Wrote {len(picked) + len(BROKEN)} VINs to {out} "
          f"({sum(1 for _, m in picked if m.lower() in EUROPEAN_MAKES)} European makes, "
          f"{len(BROKEN)} broken on purpose)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--size", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    main(a.source, a.size, a.seed)
