from fastapi.testclient import TestClient


def test_create_machine_success(client: TestClient):
    payload = {
        "code": "MILL-01",
        "name": "Heavy Duty Milling Line",
        "description": "Bay A",
        "ideal_cycle_time_seconds": 25.0,
        "is_active": True,
    }
    response = client.post("/api/machines/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "MILL-01"
    assert data["name"] == "Heavy Duty Milling Line"
    assert data["ideal_cycle_time_seconds"] == 25.0
    assert data["is_active"] is True
    assert "id" in data


def test_create_machine_duplicate_code_fails(client: TestClient, machine_factory):
    machine_factory(code="DUP-01")
    payload = {
        "code": "DUP-01",
        "name": "Duplicate Code Machine",
        "ideal_cycle_time_seconds": 10.0,
    }
    response = client.post("/api/machines/", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_machines_and_is_active_filter(client: TestClient, machine_factory):
    machine_factory(code="ACT-01", is_active=True)
    machine_factory(code="INACT-01", is_active=False)

    # List all
    res_all = client.get("/api/machines/")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Filter active only
    res_active = client.get("/api/machines/?is_active=true")
    assert res_active.status_code == 200
    assert len(res_active.json()) == 1
    assert res_active.json()[0]["code"] == "ACT-01"


def test_get_machine_by_id(client: TestClient, machine_factory):
    machine = machine_factory(code="GET-01", name="Target Machine")
    res_ok = client.get(f"/api/machines/{machine.id}")
    assert res_ok.status_code == 200
    assert res_ok.json()["code"] == "GET-01"

    res_404 = client.get("/api/machines/999999")
    assert res_404.status_code == 404


def test_update_machine_partial_and_duplicate_handling(
    client: TestClient, machine_factory
):
    m1 = machine_factory(code="M-A", name="Original A")
    m2 = machine_factory(code="M-B", name="Original B")

    # Valid partial update
    res_update = client.put(f"/api/machines/{m1.id}", json={"name": "Updated Name A"})
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Updated Name A"
    assert res_update.json()["code"] == "M-A"

    # Duplicate code update fails
    res_dup = client.put(f"/api/machines/{m1.id}", json={"code": "M-B"})
    assert res_dup.status_code == 400

    # 404 update
    res_404 = client.put("/api/machines/99999", json={"name": "Ghost"})
    assert res_404.status_code == 404


def test_delete_machine_is_soft_delete(client: TestClient, machine_factory):
    m = machine_factory(code="DEL-01", is_active=True)
    res_delete = client.delete(f"/api/machines/{m.id}")
    assert res_delete.status_code == 200
    assert res_delete.json()["is_active"] is False

    # Confirm record still exists in DB
    res_get = client.get(f"/api/machines/{m.id}")
    assert res_get.status_code == 200
    assert res_get.json()["is_active"] is False
