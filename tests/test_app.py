import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app import app  # noqa: E402


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_health():
    r = client().get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_index_has_service_name():
    r = client().get("/")
    assert r.status_code == 200
    assert r.get_json()["servis"] == "demo-app"


def test_metrics_exposed_and_counts_requests():
    c = client()
    c.get("/")
    body = c.get("/metrics").get_data(as_text=True)
    assert "demo_app_requests_total" in body
