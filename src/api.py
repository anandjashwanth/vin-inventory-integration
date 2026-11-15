"""
VIN-to-Inventory API (v2).

Serves the same pipeline as vin_integration.py over HTTP, so a dealer system can
decode one VIN as a vehicle is booked in, or a batch of up to 50 at once.

Run locally:
  uvicorn api:app --app-dir src --reload
  then open http://localhost:8000/docs for the interactive documentation.

Set VIN_OFFLINE=true to use the saved sample response instead of the live NHTSA API.
"""
import os

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

import vin_integration as v

OFFLINE_DEFAULT = os.getenv("VIN_OFFLINE", "false").lower() == "true"
MAPPING = v.load_mapping()

app = FastAPI(
    title="VIN-to-Inventory API",
    version="2.0.0",
    description="Decode, map and validate vehicle identification numbers for a dealership inventory.",
)


class VinResult(BaseModel):
    vin: str
    region: str
    status: str = Field(description='"clean" if ready to load, otherwise "exception"')
    stage: str | None = Field(default=None, description="Where the record was stopped, if it was")
    issues: list[str] = []
    record: dict[str, str] | None = Field(default=None, description="Inventory record, only when clean")


class BatchRequest(BaseModel):
    vins: list[str] = Field(min_length=1, max_length=v.BATCH_SIZE)


class BatchResponse(BaseModel):
    total: int
    clean: int
    exceptions: int
    results: list[VinResult]


def process(vins: list[str], offline: bool) -> list[VinResult]:
    """Local checks, batch decode, mapping and validation for a list of VINs."""
    vins = [x.strip().upper() for x in vins]
    results: dict[str, VinResult] = {}
    to_decode = []

    for vin in vins:
        ok, issue = v.local_check(vin)
        if ok:
            to_decode.append(vin)
        else:
            results[vin] = VinResult(vin=vin, region=v.region_of(vin), status="exception",
                                     stage="Local check", issues=[issue])

    if to_decode:
        try:
            rows = v.decode_all(list(dict.fromkeys(to_decode)), offline)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=f"Vehicle data API unavailable: {exc}")
        for row in rows:
            vin = str(row.get("VIN", "")).upper()
            record = v.map_record(row, MAPPING)
            record["vin"] = vin
            record["region"] = v.region_of(vin)
            issues = v.validate(record, row, MAPPING)
            results[vin] = VinResult(
                vin=vin,
                region=record["region"],
                status="exception" if issues else "clean",
                stage="After decode" if issues else None,
                issues=issues,
                record=None if issues else record,
            )

    return [results[x] for x in vins if x in results]


@app.get("/health")
def health():
    return {"status": "ok", "offline_default": OFFLINE_DEFAULT}


@app.get("/vins/{vin}", response_model=VinResult)
def decode_one(vin: str, offline: bool = Query(default=OFFLINE_DEFAULT)):
    return process([vin], offline)[0]


@app.post("/vins/batch", response_model=BatchResponse)
def decode_batch(body: BatchRequest, offline: bool = Query(default=OFFLINE_DEFAULT)):
    results = process(body.vins, offline)
    clean = sum(r.status == "clean" for r in results)
    return BatchResponse(total=len(results), clean=clean, exceptions=len(results) - clean, results=results)
