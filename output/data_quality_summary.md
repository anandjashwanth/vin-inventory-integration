# Data quality summary

- VINs received: **203**
- Rejected by local checks before any API call: **3** (1%)
- Sent to the API: **200**
- Clean records ready to load: **190** (94% of all VINs)
- Exceptions held back for review: **13**

## Results by region

| Region | VINs | Clean | Clean rate |
|---|---|---|---|
| North America | 112 | 104 | 93% |
| Europe | 74 | 70 | 95% |
| Asia | 17 | 16 | 94% |

## API error codes

| Code | Count |
|---|---|
| 0 | 200 |

## Fields most often missing after decode

| Field | Missing |
|---|---|
| transmission | 173 of 200 |
| series | 136 of 200 |
| drive_type | 114 of 200 |
| trim | 75 of 200 |
| cylinders | 16 of 200 |
| fuel_type | 10 of 200 |
| engine_litres | 6 of 200 |
| doors | 5 of 200 |
