from fastapi.testclient import TestClient


def test_html_views_render_successfully(client: TestClient, machine_factory):
    machine_factory()

    view_routes = [
        "/",
        "/machines",
        "/shifts",
        "/downtime-events",
        "/production-runs",
        "/reports",
        "/dashboard/table",
        "/reports/chart",
    ]

    for path in view_routes:
        response = client.get(path)
        assert response.status_code == 200, f"Route {path} failed with {response.status_code}"
        assert "text/html" in response.headers.get("content-type", "")


def test_machines_edit_view_nonexistent_id_returns_404(client: TestClient):
    response = client.get("/machines/999999/edit")
    assert response.status_code == 404


def test_machine_creation_flow_via_form_view(client: TestClient):
    form_data = {
        "code": "FORM-M1",
        "name": "Form Created Machine",
        "description": "Via HTMX form view",
        "ideal_cycle_time_seconds": 12.5,
        "is_active": "true",
    }

    post_res = client.post("/machines", data=form_data)
    assert post_res.status_code == 200
    assert "FORM-M1" in post_res.text
    assert "Form Created Machine" in post_res.text

    list_res = client.get("/machines")
    assert list_res.status_code == 200
    assert "FORM-M1" in list_res.text
    assert "Form Created Machine" in list_res.text
