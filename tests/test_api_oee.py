from datetime import datetime
from fastapi.testclient import TestClient


def test_get_machine_oee_valid_request(
    client: TestClient, machine_factory, production_run_factory
):
    machine = machine_factory(ideal_cycle_time_seconds=30.0)
    production_run_factory(
        machine_id=machine.id,
        start_time=datetime(2026, 8, 20, 8, 0, 0),
        end_time=datetime(2026, 8, 20, 16, 0, 0),
        total_units=800,
        scrap_units=40,
        ideal_cycle_time_seconds=30.0,
    )

    res = client.get(
        f"/api/oee/machine?machine_id={machine.id}&start_time=2026-08-20T08:00:00&end_time=2026-08-20T16:00:00"
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["oee"], float)
    assert isinstance(data["availability"], float)
    assert isinstance(data["performance"], float)
    assert isinstance(data["quality"], float)
    assert data["machine_id"] == machine.id


def test_get_machine_oee_invalid_time_range_returns_400(
    client: TestClient, machine_factory
):
    machine = machine_factory()
    res = client.get(
        f"/api/oee/machine?machine_id={machine.id}&start_time=2026-08-20T16:00:00&end_time=2026-08-20T08:00:00"
    )
    assert res.status_code == 400
    assert "end_time must be strictly greater than start_time" in res.json()["detail"]


def test_get_machine_oee_nonexistent_machine_returns_404(client: TestClient):
    res = client.get(
        "/api/oee/machine?machine_id=99999&start_time=2026-08-20T08:00:00&end_time=2026-08-20T16:00:00"
    )
    assert res.status_code == 404


def test_get_dashboard_oee_malformed_machine_ids_returns_400(client: TestClient):
    res = client.get(
        "/api/oee/dashboard?start_time=2026-08-20T08:00:00&end_time=2026-08-20T16:00:00&machine_ids=1,abc,3"
    )
    assert res.status_code == 400
    assert "comma-separated list of integers" in res.json()["detail"]
