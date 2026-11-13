# 2. Integration specification

## Source system
**NHTSA vPIC (Vehicle Product Information Catalog) API.** Run by the US National Highway Traffic Safety Administration. Free, no API key.

## Endpoints used
| Purpose | Method | URL |
|---|---|---|
| Decode up to 50 VINs | POST | `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/` |
| Decode one VIN (testing) | GET | `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{VIN}?format=json` |

**Batch request body (form data):** `format=json`, `data=VIN1;VIN2;VIN3`

**Response:** JSON with a `Results` list, one flat record per VIN, with fields such as `Make`, `Model`, `ModelYear`, `FuelTypePrimary`, `ErrorCode` and `ErrorText`.

## Data flow
```
VIN list (CSV)
   -> Local checks (length, characters, check digit)  -> rejects to exceptions
   -> Batch decode via API (50 per call)
   -> Map API fields to inventory fields (docs/03_data_mapping.csv)
   -> Validate (error codes, required fields, plausible year) -> issues to exceptions
   -> Clean inventory file + exceptions file + data quality summary
```

## Design decisions
| Decision | Reason |
|---|---|
| Check VINs locally before calling the API | Catches typos instantly, saves API calls, gives the user a clear reason |
| Batch calls of 50 | The API's batch limit; far fewer calls than one per VIN |
| Read `ErrorCode`, not the HTTP status | The API returns HTTP 200 even when a decode fails |
| Treat blank fields as "not supplied", not "not present" | A blank means the manufacturer did not file that data |
| Retry with back-off, 30-second timeout | Free public service with no service-level agreement |
| One-second pause between batches | Courtesy to a free service; no published hard rate limit |

## Known limitations
- **The API applies the North American check-digit rule to all VINs.** In testing, a valid European VIN came back with error code 1. Without an override, a UK dealer would see European cars wrongly rejected.
- **Coverage is strongest for vehicles sold in the US.** European-market VINs often return error code 8 (no detailed data). For a UK dealer this is a material gap. See the roadmap.
- **No uptime guarantee.** At production scale, NHTSA recommends hosting its downloadable database instead of calling the live API.

## Error codes handled
| Code | Meaning | Handling |
|---|---|---|
| 0 | Clean decode | Load if required fields are present |
| 1 | Check digit failure | Exception for North American VINs; ignored for European VINs, where the check digit is not required |
| 8 | No detailed data available | Exception; candidate for a UK data source |
| 11 | Incorrect model year | Exception |
| Multiple (e.g. "6,14") | Several issues | Exception listing all codes |
