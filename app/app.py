"""Небольшой сервис для демонстрации CI/CD: health-check и метрики Prometheus."""
import os
import time

from flask import Flask, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = Flask(__name__)

REQUESTS = Counter("demo_app_requests_total", "Количество запросов", ["endpoint"])
LATENCY = Histogram("demo_app_request_seconds", "Время обработки запроса", ["endpoint"])

VERSION = os.getenv("APP_VERSION", "dev")


@app.route("/")
def index():
    start = time.perf_counter()
    REQUESTS.labels("/").inc()
    resp = jsonify(service="demo-app", version=VERSION)
    LATENCY.labels("/").observe(time.perf_counter() - start)
    return resp


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
