from datetime import datetime
from fastapi.testclient import TestClient


def test_downtime_event_validation_and_creation(
    client: TestClient, machine_factory, downtime_reason_factory
):
    machine = machine_factory()
    reason = downtime_reason_factory()

    # Nonexistent machine -> 404
    res_no_m = client.post(
        "/api/downtime-events/",
        json={
            "machine_id": 99999,
            "reason_id": reason.id,
            "start_time": "2026-08-20T08:00:00",
        },
    )
    assert res_no_m.status_code == 404

    # Nonexistent reason -> 404
    res_no_r = client.post(
        "/api/downtime-events/",
        json={
            "machine_id": machine.id,
            "reason_id": 99999,
            "start_time": "2026-08-20T08:00:00",
        },
    )
    assert res_no_r.status_code == 404

    # Invalid end_time <= start_time -> 400
    res_bad_time = client.post(
        "/api/downtime-events/",
        json={
            "machine_id": machine.id,
            "reason_id": reason.id,
            "start_time": "2026-08-20T10:00:00",
            "end_time": "2026-08-20T09:00:00",
        },
    )
    assert res_bad_time.status_code == 400

    # Valid creation
    res_valid = client.post(
        "/api/downtime-events/",
        json={
            "machine_id": machine.id,
            "reason_id": reason.id,
            "start_time": "2026-08-20T10:00:00",
            "operator_name": "Test Op",
        },
    )
    assert res_valid.status_code == 201
    assert res_valid.json()["operator_name"] == "Test Op"
    assert res_valid.json()["end_time"] is None


def test_downtime_event_update_and_stop(
    client: TestClient, machine_factory, downtime_reason_factory, downtime_event_factory
):
    machine = machine_factory()
    reason = downtime_reason_factory()
    event = downtime_event_factory(
        machine_id=machine.id,
        reason_id=reason.id,
        start_time=datetime(2026, 8, 20, 8, 0, 0),
        end_time=None,
    )

    # Close open event by setting end_time
    res_stop = client.put(
        f"/api/downtime-events/{event.id}",
        json={"end_time": "2026-08-20T09:30:00", "notes": "Resolved valve"},
    )
    assert res_stop.status_code == 200
    assert res_stop.json()["end_time"] == "2026-08-20T09:30:00"
    assert res_stop.json()["notes"] == "Resolved valve"


def test_production_run_validation_and_creation(
    client: TestClient, machine_factory, shift_factory
):
    machine = machine_factory()
    shift = shift_factory()

    # scrap > total -> 400
    res_bad_scrap = client.post(
        "/api/production-runs/",
        json={
            "machine_id": machine.id,
            "shift_id": shift.id,
            "start_time": "2026-08-20T08:00:00",
            "total_units": 100,
            "scrap_units": 150,
            "ideal_cycle_time_seconds": 1.0,
        },
    )
    assert res_bad_scrap.status_code == 400
    assert "scrap_units cannot exceed total_units" in res_bad_scrap.json()["detail"]

    # end_time <= start_time -> 400
    res_bad_time = client.post(
        "/api/production-runs/",
        json={
            "machine_id": machine.id,
            "start_time": "2026-08-20T08:00:00",
            "end_time": "2026-08-20T08:00:00",
            "total_units": 100,
            "scrap_units": 10,
            "ideal_cycle_time_seconds": 1.0,
        },
    )
    assert res_bad_time.status_code == 400

    # Valid creation
    res_ok = client.post(
        "/api/production-runs/",
        json={
            "machine_id": machine.id,
            "shift_id": shift.id,
            "start_time": "2026-08-20T08:00:00",
            "end_time": "2026-08-20T16:00:00",
            "product_code": "SKU-99",
            "total_units": 500,
            "scrap_units": 25,
            "ideal_cycle_time_seconds": 2.5,
        },
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["product_code"] == "SKU-99"
    assert res_ok.json()["total_units"] == 500


def test_production_run_list_filters(
    client: TestClient, machine_factory, shift_factory, production_run_factory
):
    m1 = machine_factory()
    m2 = machine_factory()
    s1 = shift_factory()

    production_run_factory(
        machine_id=m1.id,
        shift_id=s1.id,
        start_time=datetime(2026, 8, 20, 8, 0, 0),
        end_time=datetime(2026, 8, 20, 16, 0, 0),
    )
    production_run_factory(
        machine_id=m2.id,
        shift_id=None,
        start_time=datetime(2026, 8, 21, 8, 0, 0),
        end_time=datetime(2026, 8, 21, 16, 0, 0),
    )

    # Filter by machine_id
    res_m1 = client.get(f"/api/production-runs/?machine_id={m1.id}")
    assert res_m1.status_code == 200
    assert len(res_m1.json()) == 1
    assert res_m1.json()[0]["machine_id"] == m1.id

    # Filter by shift_id
    res_s1 = client.get(f"/api/production-runs/?shift_id={s1.id}")
    assert res_s1.status_code == 200
    assert len(res_s1.json()) == 1

    # Filter by date range
    res_range = client.get(
        "/api/production-runs/?start_time=2026-08-21T00:00:00&end_time=2026-08-21T23:59:59"
    )
    assert res_range.status_code == 200
    assert len(res_range.json()) == 1
    assert res_range.json()[0]["machine_id"] == m2.id
