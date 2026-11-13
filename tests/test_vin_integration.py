import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import vin_integration as v


def test_check_digit_known_examples():
    assert v.expected_check_digit("1HGCM82633A004352") == "3"
    assert v.expected_check_digit("1M8GDM9AXKP042788") == "X"


def test_local_check_catches_bad_vins():
    assert v.local_check("1HGCM82633A004352") == (True, "")
    assert v.local_check("1HGCM82633A00435")[0] is False      # too short
    assert v.local_check("1HGCM82633A0O4352")[0] is False     # letter O
    assert v.local_check("1HGCM82633A004353")[0] is False     # check digit


def test_european_vin_skips_check_digit():
    assert v.region_of("WP0ZZZ99ZTS392124") == "Europe"
    assert v.local_check("WP0ZZZ99ZTS392124") == (True, "")


def test_transform_rules():
    assert v.transform("HONDA", "title") == "Honda"
    assert v.transform("2003.0", "int") == "2003"
    assert v.transform("2.995", "decimal_1dp") == "3.0"
    assert v.transform("Not Applicable", "none") == ""


def test_validate_reads_error_code_not_http_status():
    mapping = v.load_mapping()
    row = {"VIN": "WP0ZZZ99ZTS392124", "Make": "PORSCHE", "ErrorCode": "8", "ErrorText": "8 - No detailed data available currently"}
    rec = v.map_record(row, mapping); rec["region"] = "Europe"
    issues = v.validate(rec, row, mapping)
    assert any("API error code 8" in i for i in issues)
    assert any("model_year" in i for i in issues)


def test_european_check_digit_code_is_ignored():
    mapping = v.load_mapping()
    row = {"VIN": "WP0ZZZ99ZTS392124", "Make": "PORSCHE", "Model": "911", "ModelYear": "1996",
           "FuelTypePrimary": "Gasoline", "ErrorCode": "1",
           "ErrorText": "1 - Check Digit (9th position) does not calculate properly"}
    rec = v.map_record(row, mapping); rec["region"] = "Europe"
    assert v.validate(rec, row, mapping) == []
