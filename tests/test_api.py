import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from api import app  # noqa: E402

client = TestClient(app)
GOOD_US = "1HGCM82633A004352"       # Honda, decodes cleanly in the saved sample
EUROPE_NO_DATA = "WP0ZZZ99ZTS392124"  # Porsche, API returns error code 8


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_clean_vin_returns_inventory_record():
    r = client.get(f"/vins/{GOOD_US}", params={"offline": True})
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "clean"
    assert body["record"]["make"] == "Honda"
    assert body["record"]["model_year"] == "2003"


def test_lowercase_input_is_normalised():
    r = client.get(f"/vins/{GOOD_US.lower()}", params={"offline": True})
    assert r.json()["vin"] == GOOD_US


def test_bad_vin_stopped_before_api_call():
    r = client.get("/vins/1HGCM82633A00435", params={"offline": True})  # 16 characters
    body = r.json()
    assert body["status"] == "exception"
    assert body["stage"] == "Local check"
    assert "Wrong length" in body["issues"][0]


def test_api_error_code_is_reported():
    r = client.get(f"/vins/{EUROPE_NO_DATA}", params={"offline": True})
    body = r.json()
    assert body["status"] == "exception"
    assert any("API error code 8" in i for i in body["issues"])


def test_batch_counts_clean_and_exceptions():
    vins = [GOOD_US, EUROPE_NO_DATA, "1HGCM82633A0O4352"]
    r = client.post("/vins/batch", params={"offline": True}, json={"vins": vins})
    body = r.json()
    assert r.status_code == 200
    assert (body["total"], body["clean"], body["exceptions"]) == (3, 1, 2)
    assert [x["vin"] for x in body["results"]] == vins


def test_batch_rejects_more_than_50_vins():
    r = client.post("/vins/batch", json={"vins": [GOOD_US] * 51})
    assert r.status_code == 422


def test_batch_rejects_empty_list():
    r = client.post("/vins/batch", json={"vins": []})
    assert r.status_code == 422
