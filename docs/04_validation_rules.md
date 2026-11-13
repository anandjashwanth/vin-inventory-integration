# 4. Validation rules

## Stage 1: before calling the API
| Rule | Why |
|---|---|
| VIN must be exactly 17 characters | Standard VIN length since 1981 |
| Only digits and letters, never I, O or Q | These letters are excluded to avoid confusion with 1 and 0 |
| Check digit (9th character) must be correct for North American VINs | Catches most single-character typos. Not enforced for other regions, where the 9th character is not a check digit |

## Stage 2: after decoding
| Rule | Why |
|---|---|
| `ErrorCode` must be 0 | The API reports failures in the body, not the HTTP status |
| Ignore error code 1 (check digit) for European VINs | Found in testing: the API applies the North American check-digit rule to European VINs, which would wrongly reject valid vehicles |
| Required fields must be present: make, model, model_year, fuel_type | A listing cannot go live without them |
| Model year must be between 1981 and next year | Catches implausible values |

## Output of validation
- **Clean records** go to `output/inventory_clean.csv`, ready to load.
- **Exceptions** go to `output/exceptions.csv` with the stage and every reason, so a person can fix them.
