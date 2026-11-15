# VIN-to-Inventory Integration

[![CI](https://github.com/anandjashwanth/vin-inventory-integration/actions/workflows/ci.yml/badge.svg)](https://github.com/anandjashwanth/vin-inventory-integration/actions/workflows/ci.yml)

**A product-led integration project:** decoding vehicle identification numbers (VINs) through a public vehicle data API, mapping the results into a dealership inventory format, and catching data quality problems before they reach the dealer's system.

Built by **Jashwanth Anand Shankar**, drawing on my automotive data experience at Stellantis and ZF.

---

## The problem
When a dealership takes a vehicle into stock, staff often type 10 to 15 details by hand: make, model, year, fuel, engine and more. That is slow, and typing errors flow into pricing, advertising, finance and recall checks.

**Goal:** let staff enter only the VIN, fill the rest automatically, and stop bad or incomplete data at the point of entry.

## What I built
```
VIN list  ->  Local checks  ->  Batch decode (NHTSA API)  ->  Field mapping  ->  Validation
                  |                                                               |
                  +------------------->  Exceptions (with reasons)  <-------------+
                                                                                  |
                                                       Clean inventory + quality summary
```

1. **Local checks** catch invalid VINs instantly (wrong length, illegal letters, failed check digit) without spending an API call.
2. **Batch decoding** sends up to 50 VINs per request to the free NHTSA vPIC API.
3. **Field mapping** converts the API's fields into a dealer inventory format, driven by a mapping sheet rather than hard-coded rules.
4. **Validation** reads the API's error codes (failures still return HTTP 200), checks required fields and flags implausible values.
5. **Outputs:** a clean file ready to load, an exceptions file listing every reason a record was held back, and a data quality summary by region.

## Results
Ran on **203 VINs**: 200 sampled from a public US used-car auction dataset (half from European brands, half from others), plus 3 VINs broken on purpose.

| Measure | Result |
|---|---|
| Broken VINs caught by local checks, before any API call | **3 of 3** (no valid VIN wrongly rejected) |
| Valid VINs decoded by the API without an error code | **200 of 200** |
| Records complete and loaded clean | **190 of 200 (95%)** |
| Records held for review | **10 (5%)**, all missing fuel type despite a clean decode |

| Field needed for a dealer listing | Missing from the API response |
|---|---|
| Transmission | 87% |
| Drive type | 57% |
| Trim | 38% |

## Key findings
1. **A clean decode is not a complete record.** Every valid VIN returned error code 0, yet 5% still lacked a required field. Checking the error code alone would have let incomplete vehicles go live.
2. **The source cannot supply key listing details.** Transmission was missing for 87% of vehicles and drive type for 57%. Customers filter on both, so a second data source is needed for these fields.
3. **The European risk is about the market, not the brand.** European brands built for the US market decoded as well as everything else. The failure in early testing came from a European-market VIN: the API applied the North American check-digit rule and did not recognise European filler characters. I added an override so valid European VINs are not rejected on the check digit, and flagged European-market coverage for validation.
4. **Manufacturer brand is not manufacturing region.** Some European brands in the sample were built in North America, so their VINs follow North American rules. The region shown in the summary is where the vehicle was built, taken from the first VIN character.

**Limitation of the test data:** the sample is US-market. Coverage of European-market VINs, which a UK dealer mostly sees, needs validating with real UK dealer data before go-live.

## Product documents
| Document | What it covers |
|---|---|
| [Discovery](docs/01_discovery.md) | The user, their pain points and what success looks like |
| [Integration specification](docs/02_integration_spec.md) | Endpoints, data flow, design decisions and limitations |
| [Data mapping](docs/03_data_mapping.csv) | Every source field, target field, transformation and why it matters |
| [Validation rules](docs/04_validation_rules.md) | Checks before and after the API call |
| [Backlog](docs/05_backlog.md) | User stories with priorities and acceptance criteria |
| [Roadmap](docs/06_roadmap.md) | v1 built, v2 UK coverage, v3 recalls and AI-drafted listings |

## Run it yourself
```bash
pip install -r requirements.txt

# Demo without internet, using a saved illustrative sample:
python src/vin_integration.py --offline

# Live run against the NHTSA API:
python src/vin_integration.py --input data/vins.csv

# Tests and lint:
pip install -r requirements-dev.txt
python -m pytest -q
ruff check src tests
```
Results are written to the `output/` folder.

## Extension: the pipeline as an API service
The original pipeline is a batch job. A dealer system needs an answer the moment a vehicle is booked in, so this extension serves the same pipeline over HTTP.

| Endpoint | What it does |
|---|---|
| `GET /health` | Liveness check for monitoring and the container health check |
| `GET /vins/{vin}` | Decodes one VIN and returns either a clean inventory record or the reasons it was held back |
| `POST /vins/batch` | Decodes up to 50 VINs in one call (the API's batch limit), with clean and exception counts |
| `GET /docs` | Interactive documentation generated by FastAPI |

**Design choices**
- **Same logic, new interface.** The service reuses the batch pipeline's functions (local checks, mapping, validation), so the batch job and the API can never disagree.
- **Validated inputs.** Pydantic models reject an empty batch or more than 50 VINs with a clear 422 error before any work is done.
- **Business result, not HTTP error.** A bad VIN returns 200 with `status: "exception"` and the reason, because a rejected VIN is a normal outcome for the dealer, not a server failure. If the upstream API is down, the service returns 502.
- **Offline mode** (`VIN_OFFLINE=true`) serves the saved sample response, so tests and demos never depend on a free public service.

**Run it**
```bash
# Locally
uvicorn api:app --app-dir src --reload          # then open http://localhost:8000/docs

# In Docker (offline demo mode)
docker build -t vin-api .
docker run -p 8000:8000 -e VIN_OFFLINE=true vin-api
curl http://localhost:8000/vins/1HGCM82633A004352
```

**Container.** A slim Python 3.12 image that installs dependencies before copying code (so rebuilds are fast), copies only what the service needs, runs as a non-root user and includes a health check.

**Continuous integration** (`.github/workflows/ci.yml`). Every push and pull request:
1. Lints the code with ruff.
2. Runs all 14 pytest tests (6 for the pipeline, 8 for the API).
3. Builds the Docker image, starts it and smoke-tests `/health` and a real decode. The image is only trusted if it actually serves a correct answer.

## Decisions and trade-offs
- **Check before calling.** Local validation gives the user an instant, specific reason and avoids wasted calls.
- **Mapping as configuration.** Field mappings live in a CSV, so a product analyst can change them without touching code.
- **Hold back, don't guess.** Incomplete records go to review instead of going live with gaps.
- **At scale,** I would host NHTSA's downloadable database rather than depend on a free live service with no uptime guarantee.

## Tools
Python (requests), FastAPI and Pydantic, Docker, GitHub Actions, pytest, ruff, REST API (JSON), CSV-driven field mapping, Jira for the backlog, AI coding assistance for implementation.

---
*Data source: NHTSA vPIC API. This is an independent portfolio project and is not affiliated with any dealership software provider.*
